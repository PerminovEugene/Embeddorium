"""Stage 4: schedule embedding jobs for a document's chunks.

Acquires the target (CHUNKED → SCHEDULING) and, in one transaction, writes one
embed outbox event per batch of chunks (deduped per batch) plus the outbox
event that triggers ``schedule_discovered_links``. Idempotent: re-running emits
the same dedup keys, so no duplicate embedding jobs.
"""

from __future__ import annotations

from uuid import UUID

from laws_agent.clients.queue.embed_chunks_payload import EmbedChunksPayload
from laws_agent.clients.queue.logging_middleware import log_message_skipped
from laws_agent.clients.queue.pipeline_payloads import (
    ScheduleDiscoveredLinksPayload,
    ScheduleEmbeddingsPayload,
)
from laws_agent.clients.queue.queue_names import (
    EMBED_CHUNKS_ACTOR,
    EMBED_CHUNKS_QUEUE,
    SCHEDULE_DISCOVERED_LINKS_ACTOR,
    SCHEDULE_DISCOVERED_LINKS_QUEUE,
    SCHEDULE_EMBEDDINGS_ACTOR,
    SCHEDULE_EMBEDDINGS_QUEUE,
)
from laws_agent.models import CrawlTargetStatus, OutboxEvent
from laws_agent.storage.sql.sql_store import SqlStore

BATCH_SIZE = 32


def schedule_embeddings(*, crawl_target_id: str, group: str, store: SqlStore) -> None:
    payload = ScheduleEmbeddingsPayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, group=group
    )
    target_id: UUID = payload.crawl_target_id

    target = store.crawl_targets.acquire(
        target_id=target_id,
        from_statuses=[CrawlTargetStatus.CHUNKED, CrawlTargetStatus.SCHEDULING],
        to_status=CrawlTargetStatus.SCHEDULING,
    )
    if target is None:
        log_message_skipped(
            actor_name=SCHEDULE_EMBEDDINGS_ACTOR,
            queue_name=SCHEDULE_EMBEDDINGS_QUEUE,
            reason="not_in_processable_state",
            extra={"crawl_target_id": str(target_id)},
        )
        return

    document = store.documents.get_by_crawl_target(target_id)
    if document is None:
        store.crawl_targets.update_status(
            target_id=target_id,
            status=CrawlTargetStatus.FAILED_TRANSIENT,
            error="document missing",
        )
        raise RuntimeError(f"document missing for target {target_id}")

    chunks = store.chunks.list_by_document(document.id)

    links_payload = ScheduleDiscoveredLinksPayload(
        crawl_target_id=target_id, group=payload.group
    )

    with store.unit_of_work() as uow:
        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start : start + BATCH_SIZE]
            embed_payload = EmbedChunksPayload(
                document_id=document.id,
                chunk_ids=[chunk.id for chunk in batch],
                group=payload.group,
            )
            uow.add_outbox(
                OutboxEvent(
                    queue_name=EMBED_CHUNKS_QUEUE,
                    actor_name=EMBED_CHUNKS_ACTOR,
                    payload=embed_payload.to_actor_kwargs(),
                    dedup_key=f"embed:{document.id}:{start}",
                )
            )

        uow.add_outbox(
            OutboxEvent(
                queue_name=SCHEDULE_DISCOVERED_LINKS_QUEUE,
                actor_name=SCHEDULE_DISCOVERED_LINKS_ACTOR,
                payload=links_payload.to_actor_kwargs(),
                dedup_key=f"sched_links:{target_id}",
            )
        )
