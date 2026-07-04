import uuid

from backend.actors.schedule_discovered_links_actor import schedule_discovered_links
from backend.shared.clients.queue.queue_names import (
    CRAWL_FRONTIER_MANAGER_QUEUE,
    TRACK_PIPELINE_STATUS_QUEUE,
)
from backend.shared.models import (
    CrawlTargetStatus,
    DiscoveredLink,
    DiscoveredLinkStatus,
    Document,
)
from backend.tests.actors.pipeline_helpers import make_store, make_target, outbox_for_queue, uow_of


def _link(doc_id, *, url="https://emta.ee/x") -> DiscoveredLink:
    return DiscoveredLink(
        id=uuid.uuid4(),
        source_document_id=doc_id,
        source_chunk_id=uuid.uuid4(),
        raw_url=url,
        normalized_url=url,
        status=DiscoveredLinkStatus.PENDING,
    )


def test_lock_not_acquired_skips():
    store = make_store(acquired=None)
    schedule_discovered_links(
        crawl_target_id=str(uuid.uuid4()), store=store
    )
    store.unit_of_work.assert_not_called()


def test_schedules_links_marks_them_and_finalizes_last():
    # uow.document_all_chunks_embedded is a MagicMock by default (truthy), so
    # "not document_all_chunks_embedded(...)" is False and the target is
    # finalized straight to PROCESSED here — matching a document whose chunks
    # are all already embedded (or have none).
    target = make_target(status=CrawlTargetStatus.SCHEDULING)
    doc_id = uuid.uuid4()
    links = [_link(doc_id, url="https://emta.ee/a"), _link(doc_id, url="https://emta.ee/b")]
    store = make_store(acquired=target)
    store.documents.get_by_crawl_target.return_value = Document(
        id=doc_id, source_url=target.original_url
    )
    store.discovered_links.list_pending_by_document.return_value = links

    schedule_discovered_links(crawl_target_id=str(target.id), store=store)

    uow = uow_of(store)
    frontier_events = outbox_for_queue(uow, CRAWL_FRONTIER_MANAGER_QUEUE)
    assert {e.payload["url"] for e in frontier_events} == {
        "https://emta.ee/a",
        "https://emta.ee/b",
    }
    assert [e.dedup_key for e in frontier_events] == [f"frontier:{l.id}" for l in links]

    uow.mark_links_scheduled.assert_called_once_with([l.id for l in links])

    # The status decision is made inside the same unit of work, after the
    # frontier events, and re-derived from the document's chunk statuses.
    uow.document_all_chunks_embedded.assert_called_once_with(doc_id)
    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.PROCESSED)


def test_no_pending_links_still_finalizes():
    target = make_target(status=CrawlTargetStatus.SCHEDULING)
    store = make_store(acquired=target)
    store.documents.get_by_crawl_target.return_value = Document(
        id=uuid.uuid4(), source_url=target.original_url
    )
    store.discovered_links.list_pending_by_document.return_value = []

    schedule_discovered_links(crawl_target_id=str(target.id), store=store)

    uow = uow_of(store)
    assert outbox_for_queue(uow, CRAWL_FRONTIER_MANAGER_QUEUE) == []
    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.PROCESSED)


def test_pending_chunks_move_target_to_embedding_instead_of_processed():
    # A document with chunks still awaiting embed_chunks must not be marked
    # PROCESSED yet — this is the bug fix: the target waits in EMBEDDING until
    # embed_chunks finalizes it once every chunk is embedded.
    target = make_target(status=CrawlTargetStatus.SCHEDULING)
    doc_id = uuid.uuid4()
    store = make_store(acquired=target)
    store.documents.get_by_crawl_target.return_value = Document(
        id=doc_id, source_url=target.original_url
    )
    store.discovered_links.list_pending_by_document.return_value = []

    uow = uow_of(store)
    uow.document_all_chunks_embedded.return_value = False

    schedule_discovered_links(crawl_target_id=str(target.id), store=store)

    uow.document_all_chunks_embedded.assert_called_once_with(doc_id)
    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.EMBEDDING)


def test_missing_document_finalizes_to_processed():
    # No document (edge case) means there is nothing to wait on; finalize
    # immediately rather than getting stuck in EMBEDDING forever.
    target = make_target(status=CrawlTargetStatus.SCHEDULING)
    store = make_store(acquired=target)
    store.documents.get_by_crawl_target.return_value = None
    store.discovered_links.list_pending_by_document.return_value = []

    schedule_discovered_links(crawl_target_id=str(target.id), store=store)

    uow = uow_of(store)
    uow.document_all_chunks_embedded.assert_not_called()
    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.PROCESSED)


# --- pipeline status tracking ---

def test_pipeline_id_emits_tracker_event_with_links_dedup_key():
    target = make_target(status=CrawlTargetStatus.SCHEDULING)
    pipeline_id = str(uuid.uuid4())
    store = make_store(acquired=target)
    store.documents.get_by_crawl_target.return_value = Document(
        id=uuid.uuid4(), source_url=target.original_url
    )
    store.discovered_links.list_pending_by_document.return_value = []

    schedule_discovered_links(
        crawl_target_id=str(target.id),
        pipeline_id=pipeline_id,
        store=store,
    )

    uow = uow_of(store)
    tracker_events = outbox_for_queue(uow, TRACK_PIPELINE_STATUS_QUEUE)
    assert len(tracker_events) == 1
    assert tracker_events[0].payload["pipeline_id"] == pipeline_id
    assert tracker_events[0].dedup_key == f"track:{pipeline_id}:links:{target.id}"


def test_no_pipeline_id_emits_no_tracker_event():
    target = make_target(status=CrawlTargetStatus.SCHEDULING)
    store = make_store(acquired=target)
    store.documents.get_by_crawl_target.return_value = Document(
        id=uuid.uuid4(), source_url=target.original_url
    )
    store.discovered_links.list_pending_by_document.return_value = []

    schedule_discovered_links(crawl_target_id=str(target.id), store=store)

    uow = uow_of(store)
    assert outbox_for_queue(uow, TRACK_PIPELINE_STATUS_QUEUE) == []
