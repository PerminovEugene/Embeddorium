import uuid
from unittest.mock import MagicMock

from backend.actors.chunk_document_actor import chunk_document
from backend.shared.clients.queue.queue_names import SCHEDULE_EMBEDDINGS_QUEUE
from backend.shared.models import CrawlTargetStatus, Document, DocumentChunk
from backend.plugins.chunkers.base import Chunk
from backend.tests.actors.pipeline_helpers import make_store, make_target, outbox_for_queue, uow_of


def _chunker(chunks: list[Chunk]) -> MagicMock:
    chunker = MagicMock()
    chunker.chunk.return_value = chunks
    return chunker


def _store_with_document(target, *, doc_id, saved_chunks):
    store = make_store(acquired=target)
    store.documents.get_by_crawl_target.return_value = Document(
        id=doc_id, source_url=target.original_url, text_path=None
    )
    store.source_fetches.get_by_crawl_target.return_value = None
    uow_of(store).upsert_chunks.return_value = saved_chunks
    return store


def test_lock_not_acquired_skips():
    store = make_store(acquired=None)
    chunk_document(
        crawl_target_id=str(uuid.uuid4()),
        group="Estonia",
        store=store,
        chunker=_chunker([]),
    )
    store.documents.get_by_crawl_target.assert_not_called()
    store.unit_of_work.assert_not_called()


def test_happy_path_upserts_chunks_links_and_enqueues_embeddings():
    target = make_target(status=CrawlTargetStatus.PARSED)
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    saved_chunks = [
        DocumentChunk(id=chunk_id, document_id=doc_id, text="c0", chunk_index=0)
    ]
    store = _store_with_document(target, doc_id=doc_id, saved_chunks=saved_chunks)
    chunker = _chunker(
        [Chunk(text="c0 [Decl](https://emta.ee/decl)")]
    )

    chunk_document(
        crawl_target_id=str(target.id), group="Estonia", store=store, chunker=chunker
    )

    uow = uow_of(store)

    # chunks built with sequential indices
    chunk_models = uow.upsert_chunks.call_args.args[0]
    assert [c.chunk_index for c in chunk_models] == [0]
    assert chunk_models[0].document_id == doc_id

    # discovered link persisted with normalized url + parent chunk
    links = uow.upsert_discovered_links.call_args.args[0]
    assert len(links) == 1
    assert links[0].source_chunk_id == chunk_id
    assert links[0].normalized_url == "https://emta.ee/decl"
    assert links[0].anchor_text == "Decl"
    assert links[0].group == "Estonia"

    assert uow.set_status.call_args.args[1] == CrawlTargetStatus.CHUNKED

    embed_events = outbox_for_queue(uow, SCHEDULE_EMBEDDINGS_QUEUE)
    assert len(embed_events) == 1
    assert embed_events[0].dedup_key == f"sched_embed:{target.id}"


def test_no_links_still_advances_and_schedules():
    target = make_target(status=CrawlTargetStatus.PARSED)
    doc_id = uuid.uuid4()
    saved_chunks = [
        DocumentChunk(id=uuid.uuid4(), document_id=doc_id, text="c0", chunk_index=0)
    ]
    store = _store_with_document(target, doc_id=doc_id, saved_chunks=saved_chunks)
    chunker = _chunker([Chunk(text="c0")])

    chunk_document(
        crawl_target_id=str(target.id), group="Estonia", store=store, chunker=chunker
    )

    uow = uow_of(store)
    assert uow.upsert_discovered_links.call_args.args[0] == []
    assert outbox_for_queue(uow, SCHEDULE_EMBEDDINGS_QUEUE)
