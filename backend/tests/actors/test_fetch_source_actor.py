"""Tests for the merged fetch_source actor.

The web strategy fetches over HTTP and routes to parse_source; the local
strategy reads a file from disk and routes to filter_documents. Strategy
selection falls back to the target's normalized URL (``file://`` prefix)
because these messages carry no pipeline_id.
"""

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.actors.fetch_source_actor import fetch_source
from backend.plugins.fetch_source.base import SourceFetchError
from backend.shared.clients.http.failures import FailureKind, FetchFailure
from backend.shared.clients.http.fetcher import FetchResult
from backend.shared.clients.queue.queue_names import (
    FILTER_DOCUMENTS_QUEUE,
    PARSE_SOURCE_QUEUE,
)
from backend.shared.models import CrawlTargetStatus
from backend.tests.actors.pipeline_helpers import (
    make_store,
    make_target,
    outbox_for_queue,
    uow_of,
)


def _fetcher(
    result: FetchResult | None = None, error: Exception | None = None
) -> MagicMock:
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


def _make_file_target(file_path: Path):
    """A crawl target as created by the validate_source local strategy."""
    abs_path = str(file_path.resolve())
    return make_target(url=abs_path).model_copy(
        update={"normalized_url": f"file://{abs_path}"}
    )


# --- shared: acquisition ---


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


# --- web strategy ---


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
    fetcher = _fetcher(
        error=FetchFailure(FailureKind.PERMANENT, "http status 404", status=404)
    )

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

    with pytest.raises(SourceFetchError):
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


# --- local-file strategy ---


def test_local_file_saves_fetch_and_enqueues_filter(
    tmp_path: Path, monkeypatch
) -> None:
    import backend.shared.pipeline.source_files as sf

    monkeypatch.setattr(sf, "PIPELINE_RUNS_DIR", tmp_path)

    file_path = tmp_path / "501012020001.xml"
    content = "<doc><pealkiri>Sample Document</pealkiri></doc>"
    file_path.write_text(content)

    target = _make_file_target(file_path)
    store = make_store(acquired=target)
    fetcher = _fetcher()

    _run(store, fetcher, target_id=target.id)

    # The web fetcher is never touched for a file:// target.
    fetcher.fetch.assert_not_called()

    uow = uow_of(store)
    uow.upsert_source_fetch.assert_called_once()
    fetch = uow.upsert_source_fetch.call_args.args[0]
    assert fetch.crawl_target_id == target.id
    assert fetch.raw_content_path is not None
    assert (tmp_path / fetch.raw_content_path).read_text(encoding="utf-8") == content
    assert fetch.content_type == "application/xml"
    assert fetch.http_status == 0
    assert fetch.final_url == target.normalized_url
    assert fetch.content_hash

    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.FETCHED)

    filter_events = outbox_for_queue(uow, FILTER_DOCUMENTS_QUEUE)
    assert len(filter_events) == 1
    assert filter_events[0].dedup_key == f"filter:{target.id}"
    assert outbox_for_queue(uow, PARSE_SOURCE_QUEUE) == []


def test_local_missing_file_marks_failed_permanent(tmp_path: Path) -> None:
    missing_path = tmp_path / "does-not-exist.xml"
    target = _make_file_target(missing_path)
    store = make_store(acquired=target)

    _run(store, _fetcher(), target_id=target.id)  # no raise

    store.crawl_targets.update_status.assert_called_once()
    assert (
        store.crawl_targets.update_status.call_args.kwargs["status"]
        == CrawlTargetStatus.FAILED_PERMANENT
    )
    assert store.crawl_targets.update_status.call_args.kwargs["target_id"] == target.id
    store.unit_of_work.assert_not_called()
