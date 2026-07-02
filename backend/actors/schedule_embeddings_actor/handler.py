"""Stage 4: schedule embedding jobs for a document's chunks.

Acquires the target (CHUNKED → SCHEDULING) and, in one transaction, writes one
embed outbox event per batch of chunks (deduped per batch) plus the outbox
event that triggers ``schedule_discovered_links``. Idempotent: re-running emits
the same dedup keys, so no duplicate embedding jobs.

Each batch whose outbox event is newly inserted also bumps the run's
``embeddings_scheduled`` counter, which ``track_pipeline_status`` compares
against ``embeddings_completed`` (bumped by ``embed_chunks``) to detect when a
run has no more embed work outstanding.
"""

from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from backend.shared.clients.queue.embed_chunks_payload import EmbedChunksPayload
from backend.shared.clients.queue.logging_middleware import log_message_skipped
from backend.shared.clients.queue.pipeline_payloads import (
    ScheduleDiscoveredLinksPayload,
    ScheduleEmbeddingsPayload,
)
from backend.shared.clients.queue.queue_names import (
    EMBED_CHUNKS_ACTOR,
    EMBED_CHUNKS_QUEUE,
    SCHEDULE_DISCOVERED_LINKS_ACTOR,
    SCHEDULE_DISCOVERED_LINKS_QUEUE,
    SCHEDULE_EMBEDDINGS_ACTOR,
    SCHEDULE_EMBEDDINGS_QUEUE,
)
from backend.shared.models import (
    CrawlTargetStatus,
    OutboxEvent,
    ScheduleEmbeddingsSettings,
)
from backend.shared.pipeline.actor_config import load_actor_configs
from backend.shared.storage.sql.sql_store import SqlStore

# Default batch size; overridden per-run by the schedule_embeddings actor config.
BATCH_SIZE = 32


def schedule_embeddings(
    *,
    crawl_target_id: str,
    group: str,
    pipeline_id: Optional[str] = None,
    store: SqlStore,
) -> None:
    payload = ScheduleEmbeddingsPayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, group=group, pipeline_id=pipeline_id
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

    # Batch size comes from this run's actor config (falls back to the default).
    cfg = load_actor_configs(store, payload.pipeline_id)
    settings = cfg.schedule_embeddings if cfg else ScheduleEmbeddingsSettings()
    batch_size = max(1, settings.batch_size)

    links_payload = ScheduleDiscoveredLinksPayload(
        crawl_target_id=target_id,
        group=payload.group,
        pipeline_id=payload.pipeline_id,
    )

    with store.unit_of_work() as uow:
        # Only newly-inserted events (not re-deliveries) bump the run's
        # embeddings_scheduled counter, so track_pipeline_status sees an
        # exact batch count even if this message is redelivered.
        newly_scheduled = 0
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            embed_payload = EmbedChunksPayload(
                document_id=document.id,
                chunk_ids=[chunk.id for chunk in batch],
                group=payload.group,
                pipeline_id=payload.pipeline_id,
            )
            inserted = uow.add_outbox(
                OutboxEvent(
                    queue_name=EMBED_CHUNKS_QUEUE,
                    actor_name=EMBED_CHUNKS_ACTOR,
                    payload=embed_payload.to_actor_kwargs(),
                    dedup_key=f"embed:{document.id}:{start}",
                )
            )
            if inserted:
                newly_scheduled += 1

        if payload.pipeline_id is not None and newly_scheduled > 0:
            uow.increment_embeddings_scheduled(
                uuid.UUID(payload.pipeline_id), newly_scheduled
            )

        uow.add_outbox(
            OutboxEvent(
                queue_name=SCHEDULE_DISCOVERED_LINKS_QUEUE,
                actor_name=SCHEDULE_DISCOVERED_LINKS_ACTOR,
                payload=links_payload.to_actor_kwargs(),
                dedup_key=f"sched_links:{target_id}",
            )
        )
