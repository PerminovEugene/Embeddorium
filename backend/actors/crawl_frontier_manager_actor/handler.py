import logging
import uuid
from typing import Optional

from backend.actors.crawl_frontier_manager_actor.url_helper import (
    is_allowed_url,
    normalize_url,
)
from backend.shared.clients.queue.logging_middleware import log_message_skipped
from backend.shared.clients.queue.process_link_payload import ProcessLinkSourcePayload
from backend.shared.clients.queue.queue_names import (
    CRAWL_FRONTIER_MANAGER_ACTOR,
    CRAWL_FRONTIER_MANAGER_QUEUE,
    FETCH_SOURCE_ACTOR,
    FETCH_SOURCE_QUEUE,
)
from backend.shared.log_routing import build_log_dir, log_to
from backend.shared.models import (
    CrawlFrontierManagerSettings,
    CrawlTarget,
    CrawlTargetStatus,
)
from backend.shared.pipeline.actor_config import load_actor_configs
from backend.shared.storage.sql.sql_store import SqlStore

import dramatiq

logger = logging.getLogger(__name__)


def _resolve_log_dir(
    *, payload: ProcessLinkSourcePayload, normalized_url: str, store: SqlStore
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
        url=payload.url,
        normalized_url=normalized_url,
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
    payload = ProcessLinkSourcePayload.from_actor_kwargs(
        url=url,
        parent_document_id=parent_document_id,
        parent_chunk_id=parent_chunk_id,
        pipeline_id=pipeline_id,
    )

    # Convert once; None for legacy messages without a pipeline_id.
    run_uuid = uuid.UUID(payload.pipeline_id) if payload.pipeline_id else None

    # Frontier knobs from this run's actor config: whether to normalize URLs
    # before storing/dedup, and whether to apply the already-queued gate.
    cfg = load_actor_configs(store, payload.pipeline_id)
    settings = cfg.crawl_frontier_manager if cfg else CrawlFrontierManagerSettings()

    normalized_url = (
        normalize_url(payload.url) if settings.normalize_urls else payload.url
    )
    log_dir = _resolve_log_dir(
        payload=payload, normalized_url=normalized_url, store=store
    )

    with log_to(log_dir, pipeline_id=pipeline_id):
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
                actor_name=CRAWL_FRONTIER_MANAGER_ACTOR,
                queue_name=CRAWL_FRONTIER_MANAGER_QUEUE,
                reason="url_already_queued",
                extra={"normalized_url": normalized_url},
            )
            return

        if not is_allowed_url(
            payload=payload, normalized_url=normalized_url, store=store
        ):
            log_message_skipped(
                actor_name=CRAWL_FRONTIER_MANAGER_ACTOR,
                queue_name=CRAWL_FRONTIER_MANAGER_QUEUE,
                reason="url_not_allowed",
                extra={
                    "normalized_url": normalized_url,
                    "parent_document_id": str(payload.parent_document_id),
                },
            )
            return

        target = store.crawl_targets.save(
            CrawlTarget(
                pipeline_id=run_uuid,
                original_url=payload.url,
                normalized_url=normalized_url,
                status=CrawlTargetStatus.QUEUED,
                parent_document_id=payload.parent_document_id,
                parent_chunk_id=payload.parent_chunk_id,
                log_dir=log_dir,
            )
        )

        logger.info(
            "crawl_target_created id=%s url=%s log_dir=%s", target.id, url, log_dir
        )

        broker.enqueue(
            dramatiq.Message(
                queue_name=FETCH_SOURCE_QUEUE,
                actor_name=FETCH_SOURCE_ACTOR,
                args=[],
                kwargs={
                    "crawl_target_id": str(target.id),
                    "pipeline_id": payload.pipeline_id,
                },
                options={},
            )
        )
