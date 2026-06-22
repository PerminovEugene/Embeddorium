"""Stage 3: split a document into chunks and persist discovered links.

Acquires the target (PARSED → CHUNKING), splits the stored text, and in one
transaction upserts chunks (unique on document_id+chunk_index), upserts the
links found in each chunk (unique on source_chunk_id+normalized_url), advances
to CHUNKED and writes the outbox event that triggers ``schedule_embeddings``.
"""

from __future__ import annotations

from uuid import UUID

from laws_agent.actors.crawl_frontier_manager_actor.url_helper import normalize_url
from laws_agent.clients.queue.logging_middleware import log_message_skipped
from laws_agent.clients.queue.pipeline_payloads import (
    ChunkDocumentPayload,
    ScheduleEmbeddingsPayload,
)
from laws_agent.clients.queue.queue_names import (
    CHUNK_DOCUMENT_ACTOR,
    CHUNK_DOCUMENT_QUEUE,
    SCHEDULE_EMBEDDINGS_ACTOR,
    SCHEDULE_EMBEDDINGS_QUEUE,
)
from laws_agent.models import (
    CrawlTargetStatus,
    DiscoveredLink,
    DocumentChunk,
    OutboxEvent,
)
from laws_agent.parsers.text_splitter import TextSplitter
from laws_agent.storage.sql.sql_store import SqlStore


def chunk_document(
    *,
    crawl_target_id: str,
    group: str,
    store: SqlStore,
    splitter: TextSplitter,
) -> None:
    payload = ChunkDocumentPayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, group=group
    )
    target_id: UUID = payload.crawl_target_id

    target = store.crawl_targets.acquire(
        target_id=target_id,
        from_statuses=[CrawlTargetStatus.PARSED, CrawlTargetStatus.CHUNKING],
        to_status=CrawlTargetStatus.CHUNKING,
    )
    if target is None:
        log_message_skipped(
            actor_name=CHUNK_DOCUMENT_ACTOR,
            queue_name=CHUNK_DOCUMENT_QUEUE,
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

    raw_chunks = splitter.split(document.text or "")
    chunk_models = [
        DocumentChunk(document_id=document.id, text=raw.text, chunk_index=index)
        for index, raw in enumerate(raw_chunks)
    ]

    schedule_payload = ScheduleEmbeddingsPayload(
        crawl_target_id=target_id, group=payload.group
    )

    with store.unit_of_work() as uow:
        saved_chunks = uow.upsert_chunks(chunk_models)

        links: list[DiscoveredLink] = []
        for saved_chunk, raw in zip(saved_chunks, raw_chunks):
            for link in raw.links:
                links.append(
                    DiscoveredLink(
                        source_document_id=document.id,
                        source_chunk_id=saved_chunk.id,
                        raw_url=link["url"],
                        normalized_url=normalize_url(link["url"]),
                        anchor_text=link.get("label"),
                        group=payload.group,
                    )
                )
        uow.upsert_discovered_links(links)

        uow.set_status(target_id, CrawlTargetStatus.CHUNKED)
        uow.add_outbox(
            OutboxEvent(
                queue_name=SCHEDULE_EMBEDDINGS_QUEUE,
                actor_name=SCHEDULE_EMBEDDINGS_ACTOR,
                payload=schedule_payload.to_actor_kwargs(),
                dedup_key=f"sched_embed:{target_id}",
            )
        )
