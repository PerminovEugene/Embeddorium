"""Stage 5 (terminal): schedule discovered links to the crawl frontier.

Acquires the target (locks while in SCHEDULING) and, in one transaction, writes
one frontier outbox event per pending discovered link (deduped per link), marks
those links scheduled, and only then sets the target to PROCESSED. Because the
frontier events live in the same committed transaction as the PROCESSED status,
downstream work is durable/recoverable before the target is considered done.
"""

from __future__ import annotations

from uuid import UUID

from laws_agent.clients.queue.logging_middleware import log_message_skipped
from laws_agent.clients.queue.pipeline_payloads import ScheduleDiscoveredLinksPayload
from laws_agent.clients.queue.queue_names import (
    CRAWL_FRONTIER_MANAGER_ACTOR,
    CRAWL_FRONTIER_MANAGER_QUEUE,
    SCHEDULE_DISCOVERED_LINKS_ACTOR,
    SCHEDULE_DISCOVERED_LINKS_QUEUE,
)
from laws_agent.models import CrawlTargetStatus, OutboxEvent
from laws_agent.storage.sql.sql_store import SqlStore


def schedule_discovered_links(
    *, crawl_target_id: str, group: str, store: SqlStore
) -> None:
    payload = ScheduleDiscoveredLinksPayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, group=group
    )
    target_id: UUID = payload.crawl_target_id

    # Lock while in SCHEDULING without changing the status yet; PROCESSED is set
    # inside the transaction below, after the frontier events are written.
    target = store.crawl_targets.acquire(
        target_id=target_id,
        from_statuses=[CrawlTargetStatus.SCHEDULING],
        to_status=CrawlTargetStatus.SCHEDULING,
    )
    if target is None:
        log_message_skipped(
            actor_name=SCHEDULE_DISCOVERED_LINKS_ACTOR,
            queue_name=SCHEDULE_DISCOVERED_LINKS_QUEUE,
            reason="not_in_processable_state",
            extra={"crawl_target_id": str(target_id)},
        )
        return

    document = store.documents.get_by_crawl_target(target_id)
    pending = (
        store.discovered_links.list_pending_by_document(document.id)
        if document is not None
        else []
    )

    with store.unit_of_work() as uow:
        scheduled_ids = []
        for link in pending:
            frontier_payload = {
                "url": link.raw_url,
                "group": payload.group,
                "parent_document_id": str(link.source_document_id),
                "parent_chunk_id": str(link.source_chunk_id),
            }
            uow.add_outbox(
                OutboxEvent(
                    queue_name=CRAWL_FRONTIER_MANAGER_QUEUE,
                    actor_name=CRAWL_FRONTIER_MANAGER_ACTOR,
                    payload=frontier_payload,
                    dedup_key=f"frontier:{link.id}",
                )
            )
            scheduled_ids.append(link.id)

        uow.mark_links_scheduled(scheduled_ids)
        uow.set_status(target_id, CrawlTargetStatus.PROCESSED)
