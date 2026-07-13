"""Relevance gate between fetch_source and parse_source (both source types).

Acquires the target (FETCHED/FILTERING → FILTERING), loads the persisted
``SourceFetch``, extracts the document title from the XML (empty for non-XML
HTML/web content, which then falls back to body matching), and classifies it
with the keyword filter strategy (include + exclude keyword lists). When both
lists are empty or the gate is disabled every document passes through.
Documents deemed relevant advance to FILTERED and get the outbox event that
triggers ``parse_source``; the rest are marked SKIPPED with
``skip_reason="not_relevant"`` and the chain stops there.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from backend.plugins.filter_documents.registry import (
    DEFAULT_FILTER_STRATEGY,
    build_filter_strategy,
)
from backend.shared.clients.queue.logging_middleware import log_message_skipped
from backend.shared.clients.queue.pipeline_payloads import (
    FilterDocumentsPayload,
    ParseSourcePayload,
)
from backend.shared.clients.queue.queue_names import (
    FILTER_DOCUMENTS_ACTOR,
    FILTER_DOCUMENTS_QUEUE,
    PARSE_SOURCE_ACTOR,
    PARSE_SOURCE_QUEUE,
)
from backend.shared.models import (
    CrawlTargetStatus,
    FilterDocumentsSettings,
    OutboxEvent,
)
from backend.shared.parsers.xml_parser import extract_act_title
from backend.shared.pipeline.actor_config import load_actor_configs
from backend.shared.pipeline.source_files import read_source_file
from backend.shared.storage.sql.sql_store import SqlStore

logger = logging.getLogger(__name__)


def filter_documents(
    *,
    crawl_target_id: str,
    pipeline_id: Optional[str] = None,
    store: SqlStore,
) -> None:
    payload = FilterDocumentsPayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, pipeline_id=pipeline_id
    )
    target_id: UUID = payload.crawl_target_id

    target = store.crawl_targets.acquire(
        target_id=target_id,
        from_statuses=[CrawlTargetStatus.FETCHED, CrawlTargetStatus.FILTERING],
        to_status=CrawlTargetStatus.FILTERING,
    )
    if target is None:
        log_message_skipped(
            actor_name=FILTER_DOCUMENTS_ACTOR,
            queue_name=FILTER_DOCUMENTS_QUEUE,
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

    raw = read_source_file(fetch.raw_content_path)
    # extract_act_title is XML/Estonian-act specific and returns "" for HTML
    # (web) content. That is fine: the keyword strategy falls back to the raw
    # body when the title is empty, so web docs are gated on their content.
    title = extract_act_title(raw)
    logger.info("title_extracted id=%s title=%r", target_id, title)

    # The filter strategy owns the relevance decision (gate toggle + include/
    # exclude keyword matching); the actor only feeds it the extracted title
    # and raw body.
    cfg = load_actor_configs(store, payload.pipeline_id)
    settings = cfg.filter_documents if cfg else FilterDocumentsSettings()
    strategy = build_filter_strategy(
        DEFAULT_FILTER_STRATEGY,
        {
            "enabled": settings.enabled,
            "keywords": settings.keywords,
            "exclude_keywords": settings.exclude_keywords,
        },
    )

    relevant = strategy.is_relevant(title=title, text=raw)
    if not relevant:
        logger.info(
            "relevance_decision id=%s title=%r decision=skipped_not_relevant",
            target_id,
            title,
        )
        store.crawl_targets.update_status(
            target_id=target_id,
            status=CrawlTargetStatus.SKIPPED,
            skip_reason="not_relevant",
        )
        return

    logger.info("relevance_decision id=%s title=%r decision=filtered", target_id, title)

    parse_payload = ParseSourcePayload(
        crawl_target_id=target_id,
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
