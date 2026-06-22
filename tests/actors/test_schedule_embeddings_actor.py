import uuid

from laws_agent.actors.schedule_embeddings_actor import BATCH_SIZE, schedule_embeddings
from laws_agent.clients.queue.queue_names import (
    EMBED_CHUNKS_QUEUE,
    SCHEDULE_DISCOVERED_LINKS_QUEUE,
)
from laws_agent.models import CrawlTargetStatus, Document, DocumentChunk
from tests.actors.pipeline_helpers import make_store, make_target, outbox_for_queue, uow_of


def _chunks(doc_id, n):
    return [
        DocumentChunk(id=uuid.uuid4(), document_id=doc_id, text=f"c{i}", chunk_index=i)
        for i in range(n)
    ]


def test_lock_not_acquired_skips():
    store = make_store(acquired=None)
    schedule_embeddings(crawl_target_id=str(uuid.uuid4()), group="Estonia", store=store)
    store.unit_of_work.assert_not_called()


def test_single_batch_emits_one_embed_event_and_schedules_links():
    target = make_target(status=CrawlTargetStatus.CHUNKED)
    doc_id = uuid.uuid4()
    chunks = _chunks(doc_id, 2)
    store = make_store(acquired=target)
    store.documents.get_by_crawl_target.return_value = Document(
        id=doc_id, source_url=target.original_url
    )
    store.chunks.list_by_document.return_value = chunks

    schedule_embeddings(crawl_target_id=str(target.id), group="Estonia", store=store)

    uow = uow_of(store)
    embed_events = outbox_for_queue(uow, EMBED_CHUNKS_QUEUE)
    assert len(embed_events) == 1
    assert embed_events[0].payload["chunk_ids"] == [str(c.id) for c in chunks]
    assert embed_events[0].payload["group"] == "Estonia"
    assert embed_events[0].dedup_key == f"embed:{doc_id}:0"

    link_events = outbox_for_queue(uow, SCHEDULE_DISCOVERED_LINKS_QUEUE)
    assert len(link_events) == 1
    assert link_events[0].dedup_key == f"sched_links:{target.id}"


def test_multiple_batches_emit_distinct_dedup_keys():
    target = make_target(status=CrawlTargetStatus.CHUNKED)
    doc_id = uuid.uuid4()
    store = make_store(acquired=target)
    store.documents.get_by_crawl_target.return_value = Document(
        id=doc_id, source_url=target.original_url
    )
    store.chunks.list_by_document.return_value = _chunks(doc_id, BATCH_SIZE + 1)

    schedule_embeddings(crawl_target_id=str(target.id), group="Estonia", store=store)

    uow = uow_of(store)
    embed_events = outbox_for_queue(uow, EMBED_CHUNKS_QUEUE)
    assert [e.dedup_key for e in embed_events] == [
        f"embed:{doc_id}:0",
        f"embed:{doc_id}:{BATCH_SIZE}",
    ]
