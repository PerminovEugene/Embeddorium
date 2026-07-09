"""Stage 3: split a document into chunks and persist discovered links.

Acquires the target (PARSED → CHUNKING), builds a ``ChunkInput`` from the
stored parsed text (plus, when available, the raw fetched content), runs it
through the pipeline's selected chunker plugin, extracts links from every
resulting chunk's text, and in one transaction upserts chunks (unique on
document_id+chunk_index), upserts the links found in each chunk (unique on
source_chunk_id+normalized_url), advances to CHUNKED and writes the outbox
event that triggers ``schedule_embeddings``.

Loading source text, extracting links, and all persistence live here — not
in the chunker — so a chunker plugin only has to implement one near-pure
method: ``Chunker.chunk(ctx: ChunkInput) -> list[Chunk]``. See
``backend/plugins/chunkers/base.py`` for the plugin interface and
``backend/plugins/chunkers/registry.py`` for how ``chunker`` is resolved.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from backend.shared.pipeline.url_helper import normalize_url
from backend.plugins.chunkers.base import Chunker, ChunkInput
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
from backend.shared.parsers.link_extractor import LinkExtractor
from backend.shared.pipeline.source_files import read_source_file
from backend.shared.storage.sql.sql_store import SqlStore


def _build_chunk_input(*, document, target_id: UUID, store: SqlStore) -> ChunkInput:
    """Load the parsed text and, when available, the raw fetched content.

    The raw content is re-read from disk via the persisted
    ``raw_content_path`` on the source fetch — the structured tree (e.g. the
    parsed XML act) is lost once the parse stage flattens it into
    ``document.text_path`` — so structure-aware chunkers (e.g. ``legal_xml``)
    re-parse the raw bytes themselves. ``raw_content`` is ``None`` when no
    fetch row or raw file exists, which every chunker must tolerate.
    """
    raw_content: Optional[str] = None
    fetch = store.source_fetches.get_by_crawl_target(target_id)
    if fetch is not None and fetch.raw_content_path:
        raw_content = read_source_file(fetch.raw_content_path) or None

    return ChunkInput(
        text=read_source_file(document.text_path),
        raw_content=raw_content,
        source_url=document.source_url,
        language=document.language or "en",
        content_type=document.content_type,
    )


def chunk_document(
    *,
    crawl_target_id: str,
    pipeline_id: Optional[str] = None,
    store: SqlStore,
    chunker: Chunker,
) -> None:
    payload = ChunkDocumentPayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, pipeline_id=pipeline_id
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

    ctx = _build_chunk_input(document=document, target_id=target_id, store=store)
    raw_chunks = chunker.chunk(ctx)

    extractor = LinkExtractor()
    chunk_models = [
        DocumentChunk(
            document_id=document.id,
            text=raw.text,
            chunk_index=index,
            chunk_type=raw.chunk_type,
            chunk_metadata=raw.metadata,
            start_offset=raw.start_offset,
            end_offset=raw.end_offset,
        )
        for index, raw in enumerate(raw_chunks)
    ]

    schedule_payload = ScheduleEmbeddingsPayload(
        crawl_target_id=target_id,
        pipeline_id=payload.pipeline_id,
    )

    with store.unit_of_work() as uow:
        saved_chunks = uow.upsert_chunks(chunk_models)

        links = []
        for saved_chunk, raw in zip(saved_chunks, raw_chunks):
            for link in extractor.extract_links(raw.text):
                links.append(
                    DiscoveredLink(
                        source_document_id=document.id,
                        source_chunk_id=saved_chunk.id,
                        raw_url=link["url"],
                        normalized_url=normalize_url(link["url"]),
                        anchor_text=link.get("label"),
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
