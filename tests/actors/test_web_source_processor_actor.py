import uuid
from pathlib import Path
from unittest.mock import MagicMock, call

import dramatiq
import pytest

from laws_agent.models.crawl_target import CrawlTarget, CrawlTargetStatus
from laws_agent.models.document import Document
from laws_agent.models.document_chunk import DocumentChunk
from laws_agent.clients.queue.queue_names import (
    EMBED_CHUNKS_QUEUE,
    EMBED_CHUNKS_ACTOR,
    LINK_PROCESSOR_QUEUE,
    LINK_PROCESSOR_ACTOR,
)
from laws_agent.actors.web_source_processor_actor import _process_web_source

FIXTURES = Path(__file__).parent / "fixtures"


def _load_html(filename: str) -> str:
    return (FIXTURES / filename).read_text()


def _make_crawl_target(url: str = "https://emta.ee") -> CrawlTarget:
    return CrawlTarget(
        id=uuid.uuid4(),
        group="Estonia",
        original_url=url,
        normalized_url=url + "/",
        status=CrawlTargetStatus.QUEUED,
    )


def _make_store(crawl_target: CrawlTarget | None = None) -> MagicMock:
    doc_id = uuid.uuid4()
    store = MagicMock()
    store.crawl_targets.get.return_value = crawl_target
    store.documents.save.return_value = Document(
        id=doc_id, source_url=crawl_target.original_url if crawl_target else "", language="Estonia"
    )

    # Track each batch's returned chunks so tests can inspect them
    saved_batches: list[list[DocumentChunk]] = []

    def _save_many(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        result = [c.model_copy(update={"id": uuid.uuid4()}) for c in chunks]
        saved_batches.append(result)
        return result

    store.chunks.save_many.side_effect = _save_many
    store._saved_batches = saved_batches
    return store


def _make_http_get(html: str) -> MagicMock:
    response = MagicMock()
    response.text = html
    response.raise_for_status.return_value = None
    return MagicMock(return_value=response)


def _make_broker() -> MagicMock:
    return MagicMock()


def _enqueued_messages(broker: MagicMock) -> list[dramatiq.Message]:
    return [c.args[0] for c in broker.enqueue.call_args_list]


def _messages_for_queue(broker: MagicMock, queue: str) -> list[dramatiq.Message]:
    return [m for m in _enqueued_messages(broker) if m.queue_name == queue]


# --- early exit ---

def test_crawl_target_not_found_makes_no_http_call() -> None:
    store = _make_store(crawl_target=None)
    broker = _make_broker()
    http_get = MagicMock()

    _process_web_source(
        crawl_target_id=str(uuid.uuid4()),
        group="Estonia",
        store=store,
        broker=broker,
        http_get=http_get,
    )

    http_get.assert_not_called()
    store.documents.save.assert_not_called()
    broker.enqueue.assert_not_called()


# --- status transitions ---

def test_status_set_to_processing_before_fetch() -> None:
    target = _make_crawl_target()
    store = _make_store(crawl_target=target)
    broker = _make_broker()

    call_order = []
    store.crawl_targets.update_status.side_effect = lambda **kw: call_order.append(kw["status"])
    http_get = _make_http_get(_load_html("simple_page.html"))
    http_get.side_effect = lambda *a, **kw: (call_order.append("http_get"), http_get.return_value)[1]

    _process_web_source(
        crawl_target_id=str(target.id),
        group="Estonia",
        store=store,
        broker=broker,
        http_get=http_get,
    )

    assert call_order[0] == CrawlTargetStatus.PROCESSING
    assert call_order[1] == "http_get"


def test_fetch_failure_sets_status_to_failed() -> None:
    target = _make_crawl_target()
    store = _make_store(crawl_target=target)
    broker = _make_broker()
    http_get = MagicMock(side_effect=ConnectionError("timeout"))

    with pytest.raises(ConnectionError):
        _process_web_source(
            crawl_target_id=str(target.id),
            group="Estonia",
            store=store,
            broker=broker,
            http_get=http_get,
        )

    failed_calls = [
        c for c in store.crawl_targets.update_status.call_args_list
        if c.kwargs.get("status") == CrawlTargetStatus.FAILED
    ]
    assert len(failed_calls) == 1
    assert "timeout" in failed_calls[0].kwargs["error"]


def test_fetch_failure_does_not_save_document() -> None:
    target = _make_crawl_target()
    store = _make_store(crawl_target=target)
    http_get = MagicMock(side_effect=ConnectionError("timeout"))

    with pytest.raises(ConnectionError):
        _process_web_source(
            crawl_target_id=str(target.id),
            group="Estonia",
            store=store,
            broker=_make_broker(),
            http_get=http_get,
        )

    store.documents.save.assert_not_called()


def test_status_set_to_processed_with_document_id() -> None:
    target = _make_crawl_target()
    store = _make_store(crawl_target=target)

    _process_web_source(
        crawl_target_id=str(target.id),
        group="Estonia",
        store=store,
        broker=_make_broker(),
        http_get=_make_http_get(_load_html("simple_page.html")),
    )

    saved_doc: Document = store.documents.save.return_value
    processed_call = next(
        c for c in store.crawl_targets.update_status.call_args_list
        if c.kwargs.get("status") == CrawlTargetStatus.PROCESSED
    )
    assert processed_call.kwargs["document_id"] == saved_doc.id


# --- document saving ---

def test_saves_document_with_crawl_target_url() -> None:
    target = _make_crawl_target("https://emta.ee/guide")
    store = _make_store(crawl_target=target)

    _process_web_source(
        crawl_target_id=str(target.id),
        group="Estonia",
        store=store,
        broker=_make_broker(),
        http_get=_make_http_get(_load_html("simple_page.html")),
    )

    saved: Document = store.documents.save.call_args.args[0]
    assert saved.source_url == "https://emta.ee/guide"
    assert saved.language == "Estonia"


# --- chunk saving ---

def test_chunks_saved_with_correct_indices() -> None:
    target = _make_crawl_target()
    store = _make_store(crawl_target=target)

    _process_web_source(
        crawl_target_id=str(target.id),
        group="Estonia",
        store=store,
        broker=_make_broker(),
        http_get=_make_http_get(_load_html("multi_link_page.html")),
    )

    all_saved = [
        chunk
        for save_call in store.chunks.save_many.call_args_list
        for chunk in save_call.args[0]
    ]
    indices = [c.chunk_index for c in all_saved]
    assert indices == list(range(len(all_saved)))


# --- embed messages ---

def test_enqueues_one_embed_message_for_single_chunk_page() -> None:
    target = _make_crawl_target()
    store = _make_store(crawl_target=target)
    broker = _make_broker()

    _process_web_source(
        crawl_target_id=str(target.id),
        group="Estonia",
        store=store,
        broker=broker,
        http_get=_make_http_get(_load_html("simple_page.html")),
    )

    embed_messages = _messages_for_queue(broker, EMBED_CHUNKS_QUEUE)
    assert len(embed_messages) == 1
    assert embed_messages[0].actor_name == EMBED_CHUNKS_ACTOR


def test_embed_message_contains_correct_chunk_ids() -> None:
    target = _make_crawl_target()
    store = _make_store(crawl_target=target)
    broker = _make_broker()

    _process_web_source(
        crawl_target_id=str(target.id),
        group="Estonia",
        store=store,
        broker=broker,
        http_get=_make_http_get(_load_html("simple_page.html")),
    )

    saved_chunks = store._saved_batches[0]
    embed_msg = _messages_for_queue(broker, EMBED_CHUNKS_QUEUE)[0]
    assert embed_msg.kwargs["chunk_ids"] == [str(c.id) for c in saved_chunks]
    assert embed_msg.kwargs["group"] == "Estonia"


# --- link extraction (simple_page.html: 3 links in 1 chunk) ---

def test_simple_page_enqueues_link_processor_message_per_link() -> None:
    target = _make_crawl_target()
    store = _make_store(crawl_target=target)
    broker = _make_broker()

    _process_web_source(
        crawl_target_id=str(target.id),
        group="Estonia",
        store=store,
        broker=broker,
        http_get=_make_http_get(_load_html("simple_page.html")),
    )

    link_messages = _messages_for_queue(broker, LINK_PROCESSOR_QUEUE)
    enqueued_urls = {m.kwargs["url"] for m in link_messages}

    assert enqueued_urls == {
        "https://emta.ee/en/private-client/declaration",
        "https://emta.ee/en/business/simplified-account",
        "https://emta.ee/en/contact",
    }


def test_link_messages_carry_parent_document_and_chunk_ids() -> None:
    target = _make_crawl_target()
    store = _make_store(crawl_target=target)
    broker = _make_broker()

    _process_web_source(
        crawl_target_id=str(target.id),
        group="Estonia",
        store=store,
        broker=broker,
        http_get=_make_http_get(_load_html("simple_page.html")),
    )

    saved_doc: Document = store.documents.save.return_value
    # simple_page has 1 chunk, so all link messages reference that single chunk
    saved_chunk = store._saved_batches[0][0]

    for msg in _messages_for_queue(broker, LINK_PROCESSOR_QUEUE):
        assert msg.kwargs["parent_document_id"] == str(saved_doc.id)
        assert msg.kwargs["parent_chunk_id"] == str(saved_chunk.id)
        assert msg.kwargs["group"] == "Estonia"
        assert msg.actor_name == LINK_PROCESSOR_ACTOR


# --- link extraction (multi_link_page.html: 7 links across 2 chunks) ---

def test_multi_link_page_all_links_enqueued() -> None:
    target = _make_crawl_target()
    store = _make_store(crawl_target=target)
    broker = _make_broker()

    _process_web_source(
        crawl_target_id=str(target.id),
        group="Estonia",
        store=store,
        broker=broker,
        http_get=_make_http_get(_load_html("multi_link_page.html")),
    )

    link_messages = _messages_for_queue(broker, LINK_PROCESSOR_QUEUE)
    enqueued_urls = {m.kwargs["url"] for m in link_messages}

    assert enqueued_urls == {
        "https://pensionikeskus.ee/en/ii-pillar/joining",
        "https://pensionikeskus.ee/en/ii-pillar/re-enrollment",
        "https://tootukassa.ee/en/content/unemployment-insurance/contribution-rates",
        "https://emta.ee/en/business/registration/sole-proprietor",
        "https://emta.ee/en/business/vat/registration",
        "https://emta.ee/en/tax-calendar",
        "https://emta.ee/en/interest-rates",
    }


def test_multi_link_page_embed_message_contains_all_chunk_ids() -> None:
    target = _make_crawl_target()
    store = _make_store(crawl_target=target)
    broker = _make_broker()

    _process_web_source(
        crawl_target_id=str(target.id),
        group="Estonia",
        store=store,
        broker=broker,
        http_get=_make_http_get(_load_html("multi_link_page.html")),
    )

    # multi_link_page produces 2 chunks; BATCH_SIZE=32 fits both in 1 batch → 1 embed message
    embed_messages = _messages_for_queue(broker, EMBED_CHUNKS_QUEUE)
    assert len(embed_messages) == 1

    saved_chunks = store._saved_batches[0]
    assert len(saved_chunks) == 2
    assert embed_messages[0].kwargs["chunk_ids"] == [str(c.id) for c in saved_chunks]
