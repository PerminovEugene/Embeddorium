"""Tests for the validate_source actor (shared stage 0 of both chains).

The web strategy covers the old crawl_frontier_manager behavior (normalize +
dedup + origin gate); the local strategy covers path resolution, dedup and
the new exists/readable validation. Strategy selection falls back to URL
inference because these messages carry no pipeline_id.
"""

import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import dramatiq
import pytest

from backend.actors.validate_source_actor import handle
from backend.shared.clients.queue.queue_names import (
    FETCH_SOURCE_ACTOR,
    FETCH_SOURCE_QUEUE,
)
from backend.shared.models.crawl_target import CrawlTarget, CrawlTargetStatus
from backend.shared.models.document import Document


def _make_store(*, existing_target=None, parent_document=None) -> MagicMock:
    store = MagicMock()
    store.crawl_targets.find_active_by_normalized_url.return_value = existing_target
    store.documents.get.return_value = parent_document
    store.crawl_targets.save.side_effect = lambda t: t.model_copy(
        update={"id": uuid.uuid4()}
    )
    return store


def _make_broker() -> MagicMock:
    return MagicMock()


def _saved_target(store: MagicMock) -> CrawlTarget:
    return store.crawl_targets.save.call_args.args[0]


# --- web strategy: happy path ---


def test_new_root_url_saves_crawl_target() -> None:
    store = _make_store()
    broker = _make_broker()

    handle(url="https://emta.ee", store=store, broker=broker)

    store.crawl_targets.save.assert_called_once()
    saved = _saved_target(store)
    assert saved.original_url == "https://emta.ee"
    assert saved.normalized_url == "https://emta.ee/"
    assert saved.status == CrawlTargetStatus.QUEUED
    assert saved.parent_document_id is None
    assert saved.parent_chunk_id is None


def test_new_root_url_enqueues_fetch_message() -> None:
    store = _make_store()
    broker = _make_broker()

    handle(url="https://emta.ee", store=store, broker=broker)

    broker.enqueue.assert_called_once()
    message: dramatiq.Message = broker.enqueue.call_args.args[0]
    assert message.queue_name == FETCH_SOURCE_QUEUE
    assert message.actor_name == FETCH_SOURCE_ACTOR
    assert "crawl_target_id" in message.kwargs


def test_child_url_same_origin_saves_and_enqueues() -> None:
    parent_doc_id = uuid.uuid4()
    parent_doc = Document(
        id=uuid.uuid4(),
        source_url="https://emta.ee/page",
        language="et",
    )
    store = _make_store(parent_document=parent_doc)
    broker = _make_broker()

    handle(
        url="https://emta.ee/sub-page",
        parent_document_id=str(parent_doc_id),
        store=store,
        broker=broker,
    )

    store.crawl_targets.save.assert_called_once()
    broker.enqueue.assert_called_once()


# --- web strategy: deduplication ---


def test_existing_active_target_is_skipped() -> None:
    existing = CrawlTarget(
        original_url="https://emta.ee",
        normalized_url="https://emta.ee/",
        status=CrawlTargetStatus.QUEUED,
    )
    store = _make_store(existing_target=existing)
    broker = _make_broker()

    handle(url="https://emta.ee", store=store, broker=broker)

    store.crawl_targets.save.assert_not_called()
    broker.enqueue.assert_not_called()


def test_deduplication_uses_normalized_url() -> None:
    existing = CrawlTarget(
        original_url="https://emta.ee/",
        normalized_url="https://emta.ee/",
        status=CrawlTargetStatus.QUEUED,
    )
    store = _make_store(existing_target=existing)
    broker = _make_broker()

    # trailing slash stripped by normalize_url → same normalized form
    handle(url="https://emta.ee/", store=store, broker=broker)

    store.crawl_targets.save.assert_not_called()
    broker.enqueue.assert_not_called()


# --- web strategy: origin guard ---


def test_child_url_different_origin_is_rejected() -> None:
    parent_doc_id = uuid.uuid4()
    parent_doc = Document(
        id=uuid.uuid4(),
        source_url="https://emta.ee/page",
        language="et",
    )
    store = _make_store(parent_document=parent_doc)
    broker = _make_broker()

    handle(
        url="https://riigiteataja.ee/act/123",
        parent_document_id=str(parent_doc_id),
        store=store,
        broker=broker,
    )

    store.crawl_targets.save.assert_not_called()
    broker.enqueue.assert_not_called()


def test_child_url_missing_parent_document_is_rejected() -> None:
    parent_doc_id = uuid.uuid4()
    store = _make_store(parent_document=None)
    broker = _make_broker()

    handle(
        url="https://emta.ee/page",
        parent_document_id=str(parent_doc_id),
        store=store,
        broker=broker,
    )

    store.crawl_targets.save.assert_not_called()
    broker.enqueue.assert_not_called()


# --- web strategy: URL normalisation ---


def test_url_normalisation_lowercases_and_strips_trailing_slash() -> None:
    store = _make_store()
    broker = _make_broker()

    # normalize_url treats a bare host as the path component — callers are
    # expected to add the scheme before calling validate_source (ensure_scheme
    # in pipeline_launch does this). Test that a pre-schemed URL is stored
    # with the normalised form.
    handle(url="https://EMTA.EE/Path/", store=store, broker=broker)

    saved = _saved_target(store)
    assert (
        saved.normalized_url == "https://emta.ee/Path"
    )  # scheme+host lowercased, trailing slash stripped


# --- local strategy: happy path ---


def test_local_file_saves_target_and_enqueues_fetch(tmp_path: Path) -> None:
    file_path = tmp_path / "501012020001.xml"
    file_path.write_text("<doc><pealkiri>Sample Document</pealkiri></doc>")
    store = _make_store()
    broker = _make_broker()

    handle(url=str(file_path), store=store, broker=broker)

    store.crawl_targets.save.assert_called_once()
    saved = _saved_target(store)
    assert saved.original_url == str(file_path.resolve())
    assert saved.normalized_url == f"file://{file_path.resolve()}"
    assert saved.status == CrawlTargetStatus.QUEUED
    assert saved.log_dir is not None

    broker.enqueue.assert_called_once()
    message: dramatiq.Message = broker.enqueue.call_args.args[0]
    assert message.queue_name == FETCH_SOURCE_QUEUE
    assert message.actor_name == FETCH_SOURCE_ACTOR


def test_local_relative_path_is_normalized_to_absolute(
    tmp_path: Path, monkeypatch
) -> None:
    file_path = tmp_path / "501012020001.xml"
    file_path.write_text("<doc/>")
    monkeypatch.chdir(tmp_path)
    store = _make_store()
    broker = _make_broker()

    handle(url=file_path.name, store=store, broker=broker)

    saved = _saved_target(store)
    assert saved.original_url == str(file_path.resolve())
    assert Path(saved.original_url).is_absolute()


# --- local strategy: validation (exists + readable) ---


def test_local_missing_file_is_rejected(tmp_path: Path) -> None:
    missing_path = tmp_path / "does-not-exist.xml"
    store = _make_store()
    broker = _make_broker()

    handle(url=str(missing_path), store=store, broker=broker)

    store.crawl_targets.save.assert_not_called()
    broker.enqueue.assert_not_called()


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores file permissions")
def test_local_unreadable_file_is_rejected(tmp_path: Path) -> None:
    file_path = tmp_path / "locked.xml"
    file_path.write_text("<doc/>")
    file_path.chmod(0o000)
    try:
        store = _make_store()
        broker = _make_broker()

        handle(url=str(file_path), store=store, broker=broker)

        store.crawl_targets.save.assert_not_called()
        broker.enqueue.assert_not_called()
    finally:
        file_path.chmod(0o644)


def test_local_directory_is_rejected(tmp_path: Path) -> None:
    """A directory is not a fetchable file (seed-time globbing expands dirs)."""
    store = _make_store()
    broker = _make_broker()

    handle(url=str(tmp_path), store=store, broker=broker)

    store.crawl_targets.save.assert_not_called()
    broker.enqueue.assert_not_called()


# --- local strategy: deduplication ---


def test_local_dedup_skips_when_target_already_active(tmp_path: Path) -> None:
    file_path = tmp_path / "501012020001.xml"
    file_path.write_text("<doc/>")
    existing = CrawlTarget(
        original_url=str(file_path.resolve()),
        normalized_url=f"file://{file_path.resolve()}",
        status=CrawlTargetStatus.FETCHED,
    )
    store = _make_store(existing_target=existing)
    broker = _make_broker()

    handle(url=str(file_path), store=store, broker=broker)

    store.crawl_targets.save.assert_not_called()
    broker.enqueue.assert_not_called()
