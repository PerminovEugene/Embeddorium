"""Stage 3: split a document into chunks and persist discovered links.

Acquires the target (PARSED → CHUNKING), splits the stored text, and in one
transaction upserts chunks (unique on document_id+chunk_index), upserts the
links found in each chunk (unique on source_chunk_id+normalized_url), advances
to CHUNKED and writes the outbox event that triggers ``schedule_embeddings``.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from backend.actors.crawl_frontier_manager_actor.url_helper import normalize_url
from backend.shared.clients.queue.logging_middleware import log_message_skipped
from backend.shared.clients.queue.pipeline_payloads import (
    ChunkDocumentPayload,
    ScheduleEmbeddingsPayload,
)
from backend.shared.clients.queue.queue_names import (
    CHUNK_DOCUMENT_ACTOR,
    CHUNK_DOCUMENT_QUEUE,
    SCHEDULE_EMBEDDINGS_ACTOR,
    SCHEDULE_EMBEDDINGS_QUEUE,
)
from backend.shared.models import (
    CrawlTargetStatus,
    DiscoveredLink,
    DocumentChunk,
    OutboxEvent,
)
from backend.shared.parsers.legal_pipeline import LegalXmlChunker
from backend.shared.parsers.text_splitter import Chunk, TextSplitter
from backend.shared.pipeline.source_files import read_source_file
from backend.shared.storage.sql.sql_store import SqlStore

# Content types routed through the legal XML chunker (structure-aware) instead
# of the generic text splitter.
_XML_CONTENT_TYPES = {"application/xml", "text/xml"}


def _build_raw_chunks(
    *,
    document,
    target_id: UUID,
    store: SqlStore,
    splitter: TextSplitter,
    legal_chunker: Optional[LegalXmlChunker],
) -> list[Chunk]:
    """Legal XML docs are chunked by legal structure; everything else by text.

    The legal chunker needs the raw XML (the structured tree is lost once the
    parse stage flattens it into the parsed-text file at
    ``document.text_path``), so the raw content is re-read from disk via the
    persisted ``raw_content_path`` on the source fetch. Falls back to the text
    splitter when the content is not XML or cannot be parsed as a Juurakt act.
    """
    content_type = (document.content_type or "").split(";")[0].strip().lower()
    if legal_chunker is not None and content_type in _XML_CONTENT_TYPES:
        fetch = store.source_fetches.get_by_crawl_target(target_id)
        if fetch is not None and fetch.raw_content_path:
            raw = read_source_file(fetch.raw_content_path)
            if raw:
                legal_chunks = legal_chunker.split_xml(
                    raw,
                    source_url=document.source_url,
                    language=document.language or "en",
                )
                if legal_chunks:
                    return legal_chunks
    return splitter.split(read_source_file(document.text_path))


def chunk_document(
    *,
    crawl_target_id: str,
    group: str,
    pipeline_id: Optional[str] = None,
    store: SqlStore,
    splitter: TextSplitter,
    legal_chunker: Optional[LegalXmlChunker] = None,
) -> None:
    payload = ChunkDocumentPayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, group=group, pipeline_id=pipeline_id
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

    raw_chunks = _build_raw_chunks(
        document=document,
        target_id=target_id,
        store=store,
        splitter=splitter,
        legal_chunker=legal_chunker,
    )
    chunk_models = [
        DocumentChunk(
            document_id=document.id,
            text=raw.text,
            chunk_index=index,
            chunk_type=raw.chunk_type,
            chunk_metadata=raw.metadata,
        )
        for index, raw in enumerate(raw_chunks)
    ]

    schedule_payload = ScheduleEmbeddingsPayload(
        crawl_target_id=target_id,
        group=payload.group,
        pipeline_id=payload.pipeline_id,
    )

    with store.unit_of_work() as uow:
        saved_chunks = uow.upsert_chunks(chunk_models)

        links = []
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
