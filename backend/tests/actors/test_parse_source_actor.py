from __future__ import annotations

import uuid
from pathlib import Path

import pytest

import backend.actors.parse_source_actor.handler as _parse_handler
from backend.actors.parse_source_actor import parse_source
from backend.shared.clients.queue.queue_names import CHUNK_DOCUMENT_QUEUE
from backend.shared.models import CrawlTargetStatus, Document, SourceFetch
from backend.tests.actors.pipeline_helpers import (
    make_store,
    make_target,
    outbox_for_queue,
    uow_of,
)


def _fetch(
    target_id, *, content_type="text/plain", raw_content_path=None
) -> SourceFetch:
    return SourceFetch(
        crawl_target_id=target_id,
        final_url="https://emta.ee/",
        http_status=200,
        content_type=content_type,
        content_hash="abc",
        raw_content_path=raw_content_path,
    )


def test_lock_not_acquired_skips():
    store = make_store(acquired=None)

    parse_source(crawl_target_id=str(uuid.uuid4()), store=store)

    store.source_fetches.get_by_crawl_target.assert_not_called()
    store.unit_of_work.assert_not_called()


def test_missing_source_fetch_marks_transient_and_raises():
    target = make_target(status=CrawlTargetStatus.FETCHED)
    store = make_store(acquired=target)
    store.source_fetches.get_by_crawl_target.return_value = None

    with pytest.raises(RuntimeError):
        parse_source(crawl_target_id=str(target.id), store=store)

    assert (
        store.crawl_targets.update_status.call_args.kwargs["status"]
        == CrawlTargetStatus.FAILED_TRANSIENT
    )


def test_unsupported_content_type_is_skipped():
    target = make_target(status=CrawlTargetStatus.FETCHED)
    store = make_store(acquired=target)
    store.source_fetches.get_by_crawl_target.return_value = _fetch(
        target.id, content_type="application/zip"
    )

    parse_source(crawl_target_id=str(target.id), store=store)

    assert (
        store.crawl_targets.update_status.call_args.kwargs["status"]
        == CrawlTargetStatus.SKIPPED_UNSUPPORTED
    )
    store.unit_of_work.assert_not_called()


def test_filtered_target_is_acquired_for_the_file_chain(tmp_path: Path, monkeypatch):
    """FILTERED is how the local-file XML chain re-joins this stage after
    filter_documents; web targets never enter this status."""
    import backend.shared.pipeline.source_files as sf

    monkeypatch.setattr(sf, "PIPELINE_RUNS_DIR", tmp_path)
    monkeypatch.setattr(_parse_handler, "read_source_file", lambda p: "<oigusakt/>")

    target = make_target(status=CrawlTargetStatus.FILTERED)
    store = make_store(acquired=target)
    store.source_fetches.get_by_crawl_target.return_value = _fetch(
        target.id, content_type="application/xml"
    )
    uow = uow_of(store)
    uow.upsert_document.return_value = Document(
        id=uuid.uuid4(), source_url=target.original_url
    )

    parse_source(crawl_target_id=str(target.id), store=store)

    store.crawl_targets.acquire.assert_called_once()
    assert (
        CrawlTargetStatus.FILTERED
        in store.crawl_targets.acquire.call_args.kwargs["from_statuses"]
    )
    uow.set_status.assert_called_once()
    assert uow.set_status.call_args.args[1] == CrawlTargetStatus.PARSED


def test_happy_path_saves_document_and_enqueues_chunk(tmp_path: Path, monkeypatch):
    import backend.shared.pipeline.source_files as sf

    monkeypatch.setattr(sf, "PIPELINE_RUNS_DIR", tmp_path)
    monkeypatch.setattr(
        _parse_handler, "read_source_file", lambda p: "Some statute text."
    )

    target = make_target(status=CrawlTargetStatus.FETCHED)
    store = make_store(acquired=target)
    store.source_fetches.get_by_crawl_target.return_value = _fetch(target.id)
    doc_id = uuid.uuid4()
    uow = uow_of(store)
    uow.upsert_document.return_value = Document(
        id=doc_id, source_url=target.original_url
    )

    parse_source(crawl_target_id=str(target.id), store=store)

    saved_doc = uow.upsert_document.call_args.args[0]
    assert saved_doc.crawl_target_id == target.id
    assert saved_doc.language == "unknown"
    assert saved_doc.text_hash
    assert saved_doc.text_path is not None
    assert (tmp_path / saved_doc.text_path).read_text(encoding="utf-8") == "Some statute text."

    uow.set_status.assert_called_once()
    assert uow.set_status.call_args.args[1] == CrawlTargetStatus.PARSED
    assert uow.set_status.call_args.kwargs["document_id"] == doc_id

    chunk_events = outbox_for_queue(uow, CHUNK_DOCUMENT_QUEUE)
    assert len(chunk_events) == 1
    assert chunk_events[0].dedup_key == f"chunk:{target.id}"
