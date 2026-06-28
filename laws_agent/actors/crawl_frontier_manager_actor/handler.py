import logging

from laws_agent.actors.crawl_frontier_manager_actor.url_helper import (
    is_allowed_url,
    normalize_url,
)
from laws_agent.clients.queue.logging_middleware import log_message_skipped
from laws_agent.clients.queue.process_link_payload import ProcessLinkSourcePayload
from laws_agent.clients.queue.queue_names import (
    CRAWL_FRONTIER_MANAGER_ACTOR,
    CRAWL_FRONTIER_MANAGER_QUEUE,
    FETCH_SOURCE_ACTOR,
    FETCH_SOURCE_QUEUE,
)
from laws_agent.log_routing import build_log_dir, log_to
from laws_agent.models import CrawlTarget, CrawlTargetStatus
from laws_agent.pipeline.run_config import build_pipeline_run
from laws_agent.storage.sql.sql_store import SqlStore

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
    group: str,
    parent_document_id: str | None = None,
    parent_chunk_id: str | None = None,
    store: SqlStore,
    broker,
) -> None:
    payload = ProcessLinkSourcePayload.from_actor_kwargs(
        url=url,
        group=group,
        parent_document_id=parent_document_id,
        parent_chunk_id=parent_chunk_id,
    )

    normalized_url = normalize_url(payload.url)
    log_dir = _resolve_log_dir(
        payload=payload, normalized_url=normalized_url, store=store
    )

    # A seed (no parent) is the start of a pipeline run for its group: record
    # its launch configuration once. Discovered links loop back here with a
    # parent set, so they don't re-trigger it (and ensure_for_group is a no-op
    # anyway once the group's row exists).
    is_seed = (
        payload.parent_document_id is None and payload.parent_chunk_id is None
    )

    with log_to(log_dir):
        if is_seed:
            store.pipeline_runs.ensure_for_group(
                build_pipeline_run(group=payload.group, source_type="web")
            )

        existing_target = store.crawl_targets.find_active_by_normalized_url(
            group=payload.group,
            normalized_url=normalized_url,
        )
        if existing_target is not None:
            log_message_skipped(
                actor_name=CRAWL_FRONTIER_MANAGER_ACTOR,
                queue_name=CRAWL_FRONTIER_MANAGER_QUEUE,
                reason="url_already_queued",
                extra={"normalized_url": normalized_url, "group": payload.group},
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
                group=payload.group,
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
                    "group": payload.group,
                },
                options={},
            )
        )
