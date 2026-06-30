"""Tax-relevance gate between fetch_file_source and parse_source.

Acquires the target (FETCHED/FILTERING → FILTERING), loads the persisted
``SourceFetch``, extracts the act title from the XML, and classifies it with
``is_tax_related``. Tax-related acts advance to FILTERED and get the outbox
event that triggers ``parse_source``; everything else is marked SKIPPED with
``skip_reason="not_tax_related"`` and the chain stops there.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from backend.shared.clients.queue.logging_middleware import log_message_skipped
from backend.shared.clients.queue.pipeline_payloads import (
    FilterTaxActsPayload,
    ParseSourcePayload,
)
from backend.shared.clients.queue.queue_names import (
    FILTER_TAX_ACTS_ACTOR,
    FILTER_TAX_ACTS_QUEUE,
    PARSE_SOURCE_ACTOR,
    PARSE_SOURCE_QUEUE,
)
from backend.shared.models import (
    CrawlTargetStatus,
    FilterTaxActsSettings,
    OutboxEvent,
)
from backend.shared.parsers.tax_filter import is_tax_related
from backend.shared.parsers.xml_parser import extract_act_title
from backend.shared.pipeline.actor_config import load_actor_configs
from backend.shared.storage.sql.sql_store import SqlStore

logger = logging.getLogger(__name__)


def _parse_keywords(raw: str) -> list[str]:
    """Split a comma-separated keyword override into a clean list ([] if empty)."""
    return [kw.strip() for kw in raw.split(",") if kw.strip()]


def filter_tax_acts(
    *,
    crawl_target_id: str,
    group: str,
    pipeline_id: Optional[str] = None,
    store: SqlStore,
) -> None:
    payload = FilterTaxActsPayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, group=group, pipeline_id=pipeline_id
    )
    target_id: UUID = payload.crawl_target_id

    target = store.crawl_targets.acquire(
        target_id=target_id,
        from_statuses=[CrawlTargetStatus.FETCHED, CrawlTargetStatus.FILTERING],
        to_status=CrawlTargetStatus.FILTERING,
    )
    if target is None:
        log_message_skipped(
            actor_name=FILTER_TAX_ACTS_ACTOR,
            queue_name=FILTER_TAX_ACTS_QUEUE,
            reason="not_in_processable_state",
            extra={"crawl_target_id": str(target_id)},
        )
        return

    logger.info("lock_acquired id=%s status=%s", target_id, target.status)

    fetch = store.source_fetches.get_by_crawl_target(target_id)
    if fetch is None:
        store.crawl_targets.update_status(
            target_id=target_id,
            status=CrawlTargetStatus.FAILED_TRANSIENT,
            error="source fetch missing",
        )
        raise RuntimeError(f"source fetch missing for target {target_id}")

    title = extract_act_title(fetch.raw_content)
    logger.info("title_extracted id=%s title=%r", target_id, title)

    # Tax gate config: when disabled, every act passes through; a non-empty
    # keyword override replaces the curated default set.
    cfg = load_actor_configs(store, payload.pipeline_id)
    settings = cfg.filter_tax_acts if cfg else FilterTaxActsSettings()
    keywords = _parse_keywords(settings.keywords) or None

    relevant = (
        True
        if not settings.enabled
        else is_tax_related(title, text=fetch.raw_content, keywords=keywords)
    )
    if not relevant:
        logger.info(
            "tax_decision id=%s title=%r decision=skipped_not_tax_related",
            target_id,
            title,
        )
        store.crawl_targets.update_status(
            target_id=target_id,
            status=CrawlTargetStatus.SKIPPED,
            skip_reason="not_tax_related",
        )
        return

    logger.info("tax_decision id=%s title=%r decision=filtered", target_id, title)

    parse_payload = ParseSourcePayload(
        crawl_target_id=target_id,
        group=payload.group,
        pipeline_id=payload.pipeline_id,
    )

    with store.unit_of_work() as uow:
        uow.set_status(target_id, CrawlTargetStatus.FILTERED)
        uow.add_outbox(
            OutboxEvent(
                queue_name=PARSE_SOURCE_QUEUE,
                actor_name=PARSE_SOURCE_ACTOR,
                payload=parse_payload.to_actor_kwargs(),
                dedup_key=f"parse:{target_id}",
            )
        )

    logger.info("advanced_to_filtered id=%s enqueued=%s", target_id, PARSE_SOURCE_QUEUE)
