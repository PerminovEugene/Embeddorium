"""Stage 0: validate a source (web URL or local file) and admit it to the crawl.

Shared entry point of both ingestion chains. Selects a validation strategy
plugin (``backend/plugins/validate_source``) by the run's dataset
``source_type`` — web sources get URL normalization plus the same-origin
gate, local files get path resolution plus exists/readable checks — then
applies the shared steps: dedup against an existing active target, persist a
``CrawlTarget`` (QUEUED) and enqueue the ``fetch_source`` message for it.
Messages without a resolvable run config fall back to inferring the source
type from the URL scheme.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

import dramatiq

from backend.plugins.validate_source.base import (
    NormalizedSource,
    SourceValidationError,
)
from backend.plugins.validate_source.registry import build_validation_strategy
from backend.shared.clients.queue.fetch_source_payload import FetchSourcePayload
from backend.shared.clients.queue.logging_middleware import log_message_skipped
from backend.shared.clients.queue.queue_names import (
    FETCH_SOURCE_ACTOR,
    FETCH_SOURCE_QUEUE,
    VALIDATE_SOURCE_ACTOR,
    VALIDATE_SOURCE_QUEUE,
)
from backend.shared.clients.queue.validate_source_payload import ValidateSourcePayload
from backend.shared.log_routing import build_log_dir, log_to
from backend.shared.models import (
    CrawlTarget,
    CrawlTargetStatus,
    ValidateSourceSettings,
)
from backend.shared.pipeline.actor_config import (
    load_actor_configs,
    load_dataset_source_type,
)
from backend.shared.storage.sql.sql_store import SqlStore

logger = logging.getLogger(__name__)


def _infer_source_type(url: str) -> str:
    """Fallback for messages without run config: web iff the URL has an
    HTTP(S) scheme, local otherwise (bare/absolute paths, ``file://`` URLs)."""
    return "web" if url.startswith(("http://", "https://")) else "local"


def _resolve_log_dir(
    *, payload: ValidateSourcePayload, source: NormalizedSource, store: SqlStore
) -> str:
    """Compute this target's nested log_dir.

    Seeds (no parent) get a root-level folder; a child link's folder nests
    inside its parent target's folder, mirroring the discovery chain.
    """
    parent_log_dir = None
    if payload.parent_document_id is not None:
        parent_target = store.crawl_targets.get_by_document_id(
            payload.parent_document_id
        )
        if parent_target is not None:
            parent_log_dir = parent_target.log_dir

    return build_log_dir(
        url=source.original_url,
        normalized_url=source.normalized_url,
        parent_log_dir=parent_log_dir,
    )


def handle(
    *,
    url: str,
    parent_document_id: Optional[str] = None,
    parent_chunk_id: Optional[str] = None,
    pipeline_id: Optional[str] = None,
    store: SqlStore,
    broker,
) -> None:
    payload = ValidateSourcePayload.from_actor_kwargs(
        url=url,
        parent_document_id=parent_document_id,
        parent_chunk_id=parent_chunk_id,
        pipeline_id=pipeline_id,
    )

    # Convert once; None for legacy messages without a pipeline_id.
    run_uuid = uuid.UUID(payload.pipeline_id) if payload.pipeline_id else None

    cfg = load_actor_configs(store, payload.pipeline_id)
    settings = cfg.validate_source if cfg else ValidateSourceSettings()

    source_type = load_dataset_source_type(
        store, payload.pipeline_id
    ) or _infer_source_type(payload.url)
    strategy = build_validation_strategy(source_type)

    source = strategy.normalize(payload=payload, settings=settings)
    log_dir = _resolve_log_dir(payload=payload, source=source, store=store)

    with log_to(log_dir, pipeline_id=pipeline_id):
        # Shared dedup gate: when on, an already-active target with the same
        # normalized identity swallows the message.
        existing_target = (
            store.crawl_targets.find_active_by_normalized_url(
                normalized_url=source.normalized_url,
                pipeline_id=run_uuid,
            )
            if settings.dedup
            else None
        )
        if existing_target is not None:
            log_message_skipped(
                actor_name=VALIDATE_SOURCE_ACTOR,
                queue_name=VALIDATE_SOURCE_QUEUE,
                reason="url_already_queued",
                extra={"normalized_url": source.normalized_url},
            )
            return

        try:
            strategy.validate(payload=payload, source=source, store=store)
        except SourceValidationError as exc:
            log_message_skipped(
                actor_name=VALIDATE_SOURCE_ACTOR,
                queue_name=VALIDATE_SOURCE_QUEUE,
                reason=exc.reason,
                extra={
                    "normalized_url": source.normalized_url,
                    "parent_document_id": str(payload.parent_document_id),
                },
            )
            return

        target = store.crawl_targets.save(
            CrawlTarget(
                pipeline_id=run_uuid,
                original_url=source.original_url,
                normalized_url=source.normalized_url,
                status=CrawlTargetStatus.QUEUED,
                parent_document_id=payload.parent_document_id,
                parent_chunk_id=payload.parent_chunk_id,
                log_dir=log_dir,
            )
        )

        logger.info(
            "crawl_target_created id=%s url=%s source_type=%s log_dir=%s",
            target.id,
            source.original_url,
            source_type,
            log_dir,
        )

        fetch_payload = FetchSourcePayload(
            crawl_target_id=target.id,
            pipeline_id=payload.pipeline_id,
        )
        broker.enqueue(
            dramatiq.Message(
                queue_name=FETCH_SOURCE_QUEUE,
                actor_name=FETCH_SOURCE_ACTOR,
                args=[],
                kwargs=fetch_payload.to_actor_kwargs(),
                options={},
            )
        )
