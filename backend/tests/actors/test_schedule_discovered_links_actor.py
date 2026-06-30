import uuid

from backend.actors.schedule_discovered_links_actor import schedule_discovered_links
from backend.shared.clients.queue.queue_names import CRAWL_FRONTIER_MANAGER_QUEUE
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
        group="Estonia",
        status=DiscoveredLinkStatus.PENDING,
    )


def test_lock_not_acquired_skips():
    store = make_store(acquired=None)
    schedule_discovered_links(
        crawl_target_id=str(uuid.uuid4()), group="Estonia", store=store
    )
    store.unit_of_work.assert_not_called()


def test_schedules_links_marks_them_and_sets_processed_last():
    target = make_target(status=CrawlTargetStatus.SCHEDULING)
    doc_id = uuid.uuid4()
    links = [_link(doc_id, url="https://emta.ee/a"), _link(doc_id, url="https://emta.ee/b")]
    store = make_store(acquired=target)
    store.documents.get_by_crawl_target.return_value = Document(
        id=doc_id, source_url=target.original_url
    )
    store.discovered_links.list_pending_by_document.return_value = links

    schedule_discovered_links(crawl_target_id=str(target.id), group="Estonia", store=store)

    uow = uow_of(store)
    frontier_events = outbox_for_queue(uow, CRAWL_FRONTIER_MANAGER_QUEUE)
    assert {e.payload["url"] for e in frontier_events} == {
        "https://emta.ee/a",
        "https://emta.ee/b",
    }
    assert [e.dedup_key for e in frontier_events] == [f"frontier:{l.id}" for l in links]

    uow.mark_links_scheduled.assert_called_once_with([l.id for l in links])

    # PROCESSED is set inside the same unit of work, after the frontier events.
    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.PROCESSED)


def test_no_pending_links_still_marks_processed():
    target = make_target(status=CrawlTargetStatus.SCHEDULING)
    store = make_store(acquired=target)
    store.documents.get_by_crawl_target.return_value = Document(
        id=uuid.uuid4(), source_url=target.original_url
    )
    store.discovered_links.list_pending_by_document.return_value = []

    schedule_discovered_links(crawl_target_id=str(target.id), group="Estonia", store=store)

    uow = uow_of(store)
    assert outbox_for_queue(uow, CRAWL_FRONTIER_MANAGER_QUEUE) == []
    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.PROCESSED)
