"""Local-file chain entry point: read a local XML act file and seed it.

Merges "frontier create" + "fetch" into one actor because the file chain has
no link-discovery/origin dedup loop (each message names an exact file on
disk). Normalizes the path, dedups against an existing active target, creates
the ``CrawlTarget``, reads the file, and in one transaction stores the
``SourceFetch`` provenance row, advances to FETCHED and writes the outbox
event that triggers ``filter_tax_acts``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from laws_agent.clients.queue.logging_middleware import log_message_skipped
from laws_agent.clients.queue.pipeline_payloads import FilterTaxActsPayload
from laws_agent.clients.queue.process_file_payload import ProcessFileSourcePayload
from laws_agent.clients.queue.queue_names import (
    FETCH_FILE_SOURCE_ACTOR,
    FETCH_FILE_SOURCE_QUEUE,
    FILTER_TAX_ACTS_ACTOR,
    FILTER_TAX_ACTS_QUEUE,
)
from laws_agent.log_routing import build_log_dir, log_to
from laws_agent.models import CrawlTarget, CrawlTargetStatus, OutboxEvent, SourceFetch
from laws_agent.pipeline.hashing import sha256_hex
from laws_agent.storage.sql.sql_store import SqlStore

logger = logging.getLogger(__name__)


def fetch_file_source(
    *, file_path: str, group: str, store: SqlStore, broker=None
) -> None:
    payload = ProcessFileSourcePayload.from_actor_kwargs(
        file_path=file_path, group=group
    )

    abs_path = str(Path(payload.file_path).resolve())
    normalized_url = f"file://{abs_path}"

    existing_target = store.crawl_targets.find_active_by_normalized_url(
        group=payload.group,
        normalized_url=normalized_url,
    )
    if existing_target is not None:
        log_message_skipped(
            actor_name=FETCH_FILE_SOURCE_ACTOR,
            queue_name=FETCH_FILE_SOURCE_QUEUE,
            reason="url_already_queued",
            extra={"normalized_url": normalized_url, "group": payload.group},
        )
        return

    log_dir = build_log_dir(
        url=abs_path, normalized_url=normalized_url, parent_log_dir=None
    )

    with log_to(log_dir):
        target = store.crawl_targets.save(
            CrawlTarget(
                group=payload.group,
                original_url=abs_path,
                normalized_url=normalized_url,
                status=CrawlTargetStatus.FETCHING,
                log_dir=log_dir,
            )
        )
        target_id: UUID = target.id

        logger.info(
            "crawl_target_created id=%s path=%s log_dir=%s",
            target_id,
            abs_path,
            log_dir,
        )

        try:
            text = Path(abs_path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            store.crawl_targets.update_status(
                target_id=target_id,
                status=CrawlTargetStatus.FAILED_PERMANENT,
                error=str(exc),
            )
            return

        logger.info("file_read path=%s bytes=%d", abs_path, len(text.encode("utf-8")))

        fetch = SourceFetch(
            crawl_target_id=target_id,
            final_url=normalized_url,
            http_status=0,
            content_type="application/xml",
            content_hash=sha256_hex(text),
            raw_content=text,
            redirect_chain=[],
        )

        filter_payload = FilterTaxActsPayload(
            crawl_target_id=target_id, group=payload.group
        )

        with store.unit_of_work() as uow:
            uow.upsert_source_fetch(fetch)
            uow.set_status(target_id, CrawlTargetStatus.FETCHED)
            uow.add_outbox(
                OutboxEvent(
                    queue_name=FILTER_TAX_ACTS_QUEUE,
                    actor_name=FILTER_TAX_ACTS_ACTOR,
                    payload=filter_payload.to_actor_kwargs(),
                    dedup_key=f"filter:{target_id}",
                )
            )

        logger.info(
            "advanced_to_fetched id=%s enqueued=%s",
            target_id,
            FILTER_TAX_ACTS_QUEUE,
        )
