import uuid
from unittest.mock import MagicMock

import pytest

from backend.actors.fetch_source_actor import fetch_source
from backend.shared.clients.http.failures import FailureKind, FetchFailure
from backend.shared.clients.http.fetcher import FetchResult
from backend.shared.clients.queue.queue_names import PARSE_SOURCE_QUEUE
from backend.shared.models import CrawlTargetStatus
from backend.tests.actors.pipeline_helpers import make_store, make_target, outbox_for_queue, uow_of


def _fetcher(result: FetchResult | None = None, error: Exception | None = None) -> MagicMock:
    fetcher = MagicMock()
    if error is not None:
        fetcher.fetch.side_effect = error
    else:
        fetcher.fetch.return_value = result or FetchResult(
            final_url="https://emta.ee/",
            status_code=200,
            content_type="text/html; charset=utf-8",
            content="<html><body>hi</body></html>",
            redirect_chain=[],
        )
    return fetcher


def _run(store, fetcher, *, target_id=None, insecure=lambda url: False):
    fetch_source(
        crawl_target_id=str(target_id or uuid.uuid4()),
        store=store,
        fetcher=fetcher,
        insecure_tls_policy=insecure,
    )


def test_target_not_found_makes_no_fetch():
    store = make_store(acquired=make_target())
    store.crawl_targets.get.return_value = None
    fetcher = _fetcher()

    _run(store, fetcher)

    fetcher.fetch.assert_not_called()
    store.crawl_targets.acquire.assert_not_called()


def test_lock_not_acquired_skips():
    store = make_store(acquired=None)
    fetcher = _fetcher()

    _run(store, fetcher)

    fetcher.fetch.assert_not_called()
    store.unit_of_work.assert_not_called()


def test_happy_path_saves_fetch_and_enqueues_parse():
    target = make_target()
    store = make_store(acquired=target)
    fetcher = _fetcher()

    _run(store, fetcher, target_id=target.id)

    uow = uow_of(store)
    uow.upsert_source_fetch.assert_called_once()
    fetch = uow.upsert_source_fetch.call_args.args[0]
    assert fetch.crawl_target_id == target.id
    assert fetch.content_hash  # hashed
    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.FETCHED)

    parse_events = outbox_for_queue(uow, PARSE_SOURCE_QUEUE)
    assert len(parse_events) == 1
    assert parse_events[0].dedup_key == f"parse:{target.id}"


def test_unsupported_content_type_is_skipped_permanently():
    target = make_target()
    store = make_store(acquired=target)
    fetcher = _fetcher(
        FetchResult(
            final_url="https://emta.ee/x.pdf",
            status_code=200,
            content_type="application/pdf",
            content="%PDF-1.4",
            redirect_chain=[],
        )
    )

    _run(store, fetcher, target_id=target.id)

    store.crawl_targets.update_status.assert_called_once()
    assert (
        store.crawl_targets.update_status.call_args.kwargs["status"]
        == CrawlTargetStatus.SKIPPED_UNSUPPORTED
    )
    store.unit_of_work.assert_not_called()


def test_permanent_failure_does_not_raise():
    target = make_target()
    store = make_store(acquired=target)
    fetcher = _fetcher(error=FetchFailure(FailureKind.PERMANENT, "http status 404", status=404))

    _run(store, fetcher, target_id=target.id)  # no raise

    assert (
        store.crawl_targets.update_status.call_args.kwargs["status"]
        == CrawlTargetStatus.FAILED_PERMANENT
    )
    store.unit_of_work.assert_not_called()


def test_transient_failure_marks_and_raises():
    target = make_target()
    store = make_store(acquired=target)
    fetcher = _fetcher(error=FetchFailure(FailureKind.TRANSIENT, "connection error"))

    with pytest.raises(FetchFailure):
        _run(store, fetcher, target_id=target.id)

    assert (
        store.crawl_targets.update_status.call_args.kwargs["status"]
        == CrawlTargetStatus.FAILED_TRANSIENT
    )


def test_insecure_tls_policy_is_passed_to_fetcher():
    target = make_target()
    store = make_store(acquired=target)
    fetcher = _fetcher()

    _run(store, fetcher, target_id=target.id, insecure=lambda url: True)

    assert fetcher.fetch.call_args.kwargs["allow_insecure_tls"] is True
