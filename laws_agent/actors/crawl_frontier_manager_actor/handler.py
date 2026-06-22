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
from laws_agent.models import CrawlTarget, CrawlTargetStatus
from laws_agent.storage.sql.sql_store import SqlStore

import dramatiq


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

    if not is_allowed_url(payload=payload, normalized_url=normalized_url, store=store):
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
        )
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
