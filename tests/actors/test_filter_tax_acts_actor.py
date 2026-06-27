import uuid

import pytest

from laws_agent.actors.filter_tax_acts_actor import filter_tax_acts
from laws_agent.clients.queue.queue_names import PARSE_SOURCE_QUEUE
from laws_agent.models import CrawlTargetStatus, SourceFetch
from tests.actors.pipeline_helpers import (
    make_store,
    make_target,
    outbox_for_queue,
    uow_of,
)


def _fetch(target_id, *, content: str) -> SourceFetch:
    return SourceFetch(
        crawl_target_id=target_id,
        final_url=f"file:///tmp/{target_id}.xml",
        http_status=0,
        content_type="application/xml",
        content_hash="abc",
        raw_content=content,
    )


_TAX_ACT_XML = "<oigusakt><pealkiri>Income Tax Act</pealkiri></oigusakt>"
_NON_TAX_ACT_XML = "<oigusakt><pealkiri>Aliens Act</pealkiri></oigusakt>"


def test_lock_not_acquired_skips():
    store = make_store(acquired=None)

    filter_tax_acts(crawl_target_id=str(uuid.uuid4()), group="Estonia", store=store)

    store.source_fetches.get_by_crawl_target.assert_not_called()
    store.unit_of_work.assert_not_called()


def test_missing_source_fetch_marks_transient_and_raises():
    target = make_target(status=CrawlTargetStatus.FETCHED)
    store = make_store(acquired=target)
    store.source_fetches.get_by_crawl_target.return_value = None

    with pytest.raises(RuntimeError):
        filter_tax_acts(crawl_target_id=str(target.id), group="Estonia", store=store)

    assert (
        store.crawl_targets.update_status.call_args.kwargs["status"]
        == CrawlTargetStatus.FAILED_TRANSIENT
    )


def test_tax_act_advances_to_filtered_and_enqueues_parse():
    target = make_target(status=CrawlTargetStatus.FETCHED)
    store = make_store(acquired=target)
    store.source_fetches.get_by_crawl_target.return_value = _fetch(
        target.id, content=_TAX_ACT_XML
    )

    filter_tax_acts(crawl_target_id=str(target.id), group="Estonia", store=store)

    uow = uow_of(store)
    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.FILTERED)

    parse_events = outbox_for_queue(uow, PARSE_SOURCE_QUEUE)
    assert len(parse_events) == 1
    assert parse_events[0].dedup_key == f"parse:{target.id}"

    store.crawl_targets.update_status.assert_not_called()


def test_non_tax_act_is_skipped_without_outbox():
    target = make_target(status=CrawlTargetStatus.FETCHED)
    store = make_store(acquired=target)
    store.source_fetches.get_by_crawl_target.return_value = _fetch(
        target.id, content=_NON_TAX_ACT_XML
    )

    filter_tax_acts(crawl_target_id=str(target.id), group="Estonia", store=store)

    store.crawl_targets.update_status.assert_called_once_with(
        target_id=target.id,
        status=CrawlTargetStatus.SKIPPED,
        skip_reason="not_tax_related",
    )
    store.unit_of_work.assert_not_called()
