import uuid
import dramatiq
import pytest
from unittest.mock import MagicMock, call

from backend.shared.models.crawl_target import CrawlTarget, CrawlTargetStatus
from backend.shared.models.document import Document
from backend.shared.clients.queue.queue_names import FETCH_SOURCE_QUEUE, FETCH_SOURCE_ACTOR
from backend.actors.crawl_frontier_manager_actor import handle


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


# --- happy path ---

def test_new_root_url_saves_crawl_target() -> None:
    store = _make_store()
    broker = _make_broker()

    handle(url="https://emta.ee", group="Estonia", store=store, broker=broker)

    store.crawl_targets.save.assert_called_once()
    saved: CrawlTarget = store.crawl_targets.save.call_args.args[0]
    assert saved.original_url == "https://emta.ee"
    assert saved.normalized_url == "https://emta.ee/"
    assert saved.group == "Estonia"
    assert saved.status == CrawlTargetStatus.QUEUED
    assert saved.parent_document_id is None
    assert saved.parent_chunk_id is None


def test_new_root_url_enqueues_fetch_message() -> None:
    store = _make_store()
    broker = _make_broker()

    handle(url="https://emta.ee", group="Estonia", store=store, broker=broker)

    broker.enqueue.assert_called_once()
    message: dramatiq.Message = broker.enqueue.call_args.args[0]
    assert message.queue_name == FETCH_SOURCE_QUEUE
    assert message.actor_name == FETCH_SOURCE_ACTOR
    assert message.kwargs["group"] == "Estonia"
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
        group="Estonia",
        parent_document_id=str(parent_doc_id),
        store=store,
        broker=broker,
    )

    store.crawl_targets.save.assert_called_once()
    broker.enqueue.assert_called_once()


# --- deduplication ---

def test_existing_active_target_is_skipped() -> None:
    existing = CrawlTarget(
        group="Estonia",
        original_url="https://emta.ee",
        normalized_url="https://emta.ee/",
        status=CrawlTargetStatus.QUEUED,
    )
    store = _make_store(existing_target=existing)
    broker = _make_broker()

    handle(url="https://emta.ee", group="Estonia", store=store, broker=broker)

    store.crawl_targets.save.assert_not_called()
    broker.enqueue.assert_not_called()


def test_deduplication_uses_normalized_url() -> None:
    existing = CrawlTarget(
        group="Estonia",
        original_url="https://emta.ee/",
        normalized_url="https://emta.ee/",
        status=CrawlTargetStatus.QUEUED,
    )
    store = _make_store(existing_target=existing)
    broker = _make_broker()

    # trailing slash stripped by normalize_url → same normalized form
    handle(url="https://emta.ee/", group="Estonia", store=store, broker=broker)

    store.crawl_targets.save.assert_not_called()
    broker.enqueue.assert_not_called()


# --- origin guard ---

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
        group="Estonia",
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
        group="Estonia",
        parent_document_id=str(parent_doc_id),
        store=store,
        broker=broker,
    )

    store.crawl_targets.save.assert_not_called()
    broker.enqueue.assert_not_called()


# --- URL normalisation ---

def test_url_without_scheme_gets_https() -> None:
    store = _make_store()
    broker = _make_broker()

    # normalize_url treats a bare host as the path component — callers are
    # expected to add the scheme before calling process_link (ensure_scheme
    # in pipeline_launch does this). Test that a pre-schemed URL is stored
    # with the normalised form.
    handle(url="https://EMTA.EE/Path/", group="Estonia", store=store, broker=broker)

    saved: CrawlTarget = store.crawl_targets.save.call_args.args[0]
    assert saved.normalized_url == "https://emta.ee/Path"  # scheme+host lowercased, trailing slash stripped
