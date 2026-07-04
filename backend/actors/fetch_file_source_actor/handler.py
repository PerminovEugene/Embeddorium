"""Local-file chain entry point: read a local XML act file and seed it.

Merges "frontier create" + "fetch" into one actor because the file chain has
no link-discovery/origin dedup loop (each message names an exact file on
disk). Normalizes the path, dedups against an existing active target, creates
the ``CrawlTarget``, reads the file, and in one transaction stores the
``SourceFetch`` provenance row, advances to FETCHED and writes the outbox
event that triggers ``filter_documents``.
"""

from __future__ import annotations

import logging
import uuid as _uuid_mod
from pathlib import Path
from typing import Optional
from uuid import UUID

from backend.shared.clients.queue.logging_middleware import log_message_skipped
from backend.shared.clients.queue.pipeline_payloads import FilterDocumentsPayload
from backend.shared.clients.queue.process_file_payload import ProcessFileSourcePayload
from backend.shared.clients.queue.queue_names import (
    FETCH_FILE_SOURCE_ACTOR,
    FETCH_FILE_SOURCE_QUEUE,
    FILTER_DOCUMENTS_ACTOR,
    FILTER_DOCUMENTS_QUEUE,
)
from backend.shared.log_routing import build_log_dir, log_to
from backend.shared.models import (
    CrawlTarget,
    CrawlTargetStatus,
    FetchFileSourceSettings,
    OutboxEvent,
    SourceFetch,
)
from backend.shared.pipeline.actor_config import load_actor_configs
from backend.shared.pipeline.hashing import sha256_hex
from backend.shared.pipeline.source_files import write_source_file
from backend.shared.storage.sql.sql_store import SqlStore

logger = logging.getLogger(__name__)


def fetch_file_source(
    *, file_path: str, pipeline_id: Optional[str] = None,
    store: SqlStore, broker=None
) -> None:
    payload = ProcessFileSourcePayload.from_actor_kwargs(
        file_path=file_path, pipeline_id=pipeline_id
    )

    logger.info(
        "payload %s",
        payload
    )

    # Convert once; None for legacy messages without a pipeline_id.
    run_uuid = _uuid_mod.UUID(payload.pipeline_id) if payload.pipeline_id else None

    logger.info(
            "PATH =%s",
            payload.file_path,
        )
    abs_path = str(Path(payload.file_path).resolve())
    normalized_url = f"file://{abs_path}"

    # dedup gate is configurable per run; when off, the same file can be
    # re-ingested into a fresh target.
    cfg = load_actor_configs(store, payload.pipeline_id)
    settings = cfg.fetch_file_source if cfg else FetchFileSourceSettings()

    existing_target = (
        store.crawl_targets.find_active_by_normalized_url(
            normalized_url=normalized_url,
            pipeline_id=run_uuid,
        )
        if settings.dedup
        else None
    )
    if existing_target is not None:
        log_message_skipped(
            actor_name=FETCH_FILE_SOURCE_ACTOR,
            queue_name=FETCH_FILE_SOURCE_QUEUE,
            reason="url_already_queued",
            extra={"normalized_url": normalized_url},
        )
        return

    log_dir = build_log_dir(
        url=abs_path, normalized_url=normalized_url, parent_log_dir=None
    )

    with log_to(log_dir, pipeline_id=payload.pipeline_id):
        target = store.crawl_targets.save(
            CrawlTarget(
                pipeline_id=run_uuid,
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

        raw_path = write_source_file(
            pipeline_id=payload.pipeline_id,
            source_id=str(target_id),
            kind="raw",
            content=text,
            extension="xml",
        )

        fetch = SourceFetch(
            crawl_target_id=target_id,
            final_url=normalized_url,
            http_status=0,
            content_type="application/xml",
            content_hash=sha256_hex(text),
            raw_content_path=raw_path,
            redirect_chain=[],
        )

        filter_payload = FilterDocumentsPayload(
            crawl_target_id=target_id,
            pipeline_id=payload.pipeline_id,
        )

        with store.unit_of_work() as uow:
            uow.upsert_source_fetch(fetch)
            uow.set_status(target_id, CrawlTargetStatus.FETCHED)
            uow.add_outbox(
                OutboxEvent(
                    queue_name=FILTER_DOCUMENTS_QUEUE,
                    actor_name=FILTER_DOCUMENTS_ACTOR,
                    payload=filter_payload.to_actor_kwargs(),
                    dedup_key=f"filter:{target_id}",
                )
            )

        logger.info(
            "advanced_to_fetched id=%s enqueued=%s",
            target_id,
            FILTER_DOCUMENTS_QUEUE,
        )
