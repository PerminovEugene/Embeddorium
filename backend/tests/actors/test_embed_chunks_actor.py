import uuid
from unittest.mock import MagicMock, call

import pytest

from backend.shared.clients.queue.queue_names import TRACK_PIPELINE_STATUS_QUEUE
from backend.shared.models.document_chunk import DocumentChunk
from backend.actors.embed_chunks_actor.handler import (
    embed_chunks as _embed_chunks,
    BATCH_SIZE,
)
from backend.tests.actors.pipeline_helpers import outbox_for_queue, uow_of


def _make_chunk(index: int, document_id: uuid.UUID) -> DocumentChunk:
    return DocumentChunk(
        id=uuid.uuid4(),
        document_id=document_id,
        text=f"chunk text {index}",
        chunk_index=index,
    )


def _make_chunks(n: int, document_id: uuid.UUID | None = None) -> list[DocumentChunk]:
    doc_id = document_id or uuid.uuid4()
    return [_make_chunk(i, doc_id) for i in range(n)]


def _make_model(chunks_per_call: list[int] | None = None) -> MagicMock:
    """Return a mock model whose encode() yields one fake embedding per input text."""
    model = MagicMock()
    model.encode.side_effect = lambda texts, **kw: [
        MagicMock(**{"tolist.return_value": [0.1, 0.2, 0.3, 0.4]})
        for _ in texts
    ]
    return model


def _make_store(chunks: list[DocumentChunk]) -> MagicMock:
    store = MagicMock()
    store.chunks.get_many.return_value = chunks
    return store


def _make_vector_store() -> MagicMock:
    return MagicMock()


def _call(
    *,
    chunks: list[DocumentChunk],
    document_id: uuid.UUID | None = None,
    model_size: int = 4,
    pipeline_id: str | None = None,
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Run _embed_chunks with mocked deps, return (store, vector_store, model)."""
    doc_id = document_id or uuid.uuid4()
    chunk_ids = [str(c.id) for c in chunks]

    store = _make_store(chunks)
    vector_store = _make_vector_store()
    model = _make_model()

    _embed_chunks(
        document_id=str(doc_id),
        chunk_ids=chunk_ids,
        store=store,
        vector_store=vector_store,
        model=model,
        model_size=model_size,
        pipeline_id=pipeline_id,
    )

    return store, vector_store, model


# --- collection setup ---

def test_creates_vector_collection_with_model_size() -> None:
    chunks = _make_chunks(2)
    _, vector_store, _ = _call(chunks=chunks, model_size=4096)
    vector_store.create_collection.assert_called_once_with(4096)


# --- chunk fetching ---

def test_fetches_chunks_by_parsed_uuids() -> None:
    doc_id = uuid.uuid4()
    chunks = _make_chunks(3, doc_id)
    chunk_ids = [str(c.id) for c in chunks]

    store = _make_store(chunks)
    vector_store = _make_vector_store()
    model = _make_model()

    _embed_chunks(
        document_id=str(doc_id),
        chunk_ids=chunk_ids,
        store=store,
        vector_store=vector_store,
        model=model,
        model_size=4,
    )

    called_ids = store.chunks.get_many.call_args.args[0]
    assert called_ids == [uuid.UUID(cid) for cid in chunk_ids]


def test_empty_chunk_list_skips_encode_and_upsert() -> None:
    _, vector_store, model = _call(chunks=[])
    model.encode.assert_not_called()
    vector_store.upsert.assert_not_called()


# --- encoding ---

def test_encodes_chunk_texts_in_order() -> None:
    chunks = _make_chunks(3)
    _, _, model = _call(chunks=chunks)

    model.encode.assert_called_once()
    encoded_texts = model.encode.call_args.args[0]
    assert encoded_texts == [c.text for c in chunks]


def test_encode_called_with_correct_kwargs() -> None:
    chunks = _make_chunks(2)
    _, _, model = _call(chunks=chunks)

    _, kwargs = model.encode.call_args
    assert kwargs["batch_size"] == BATCH_SIZE
    assert kwargs["show_progress_bar"] is False
    assert kwargs["normalize_embeddings"] is True


# --- upsert payloads ---

def test_upsert_called_once_for_single_batch() -> None:
    chunks = _make_chunks(3)
    _, vector_store, _ = _call(chunks=chunks)
    vector_store.upsert.assert_called_once()


def test_upsert_vectors_come_from_model_encode() -> None:
    chunks = _make_chunks(2)
    _, vector_store, _ = _call(chunks=chunks)

    vectors = vector_store.upsert.call_args.kwargs["vectors"]
    assert vectors == [[0.1, 0.2, 0.3, 0.4], [0.1, 0.2, 0.3, 0.4]]


def test_upsert_payload_contains_correct_metadata() -> None:
    doc_id = uuid.uuid4()
    chunks = _make_chunks(2, doc_id)
    _, vector_store, _ = _call(chunks=chunks, document_id=doc_id)

    payloads = vector_store.upsert.call_args.kwargs["payloads"]
    assert len(payloads) == 2

    for chunk, payload in zip(chunks, payloads):
        assert payload["chunk_id"] == str(chunk.id)
        assert payload["document_id"] == str(doc_id)
        assert payload["chunk_index"] == chunk.chunk_index


def test_upsert_uses_chunk_ids_as_point_ids() -> None:
    # Deterministic point ids make re-embedding idempotent (overwrite, not dup).
    doc_id = uuid.uuid4()
    chunks = _make_chunks(2, doc_id)
    _, vector_store, _ = _call(chunks=chunks, document_id=doc_id)

    ids = vector_store.upsert.call_args.kwargs["ids"]
    assert ids == [str(c.id) for c in chunks]


# --- batching ---

def test_large_input_is_split_into_batches() -> None:
    n = BATCH_SIZE + 5
    chunks = _make_chunks(n)
    _, vector_store, model = _call(chunks=chunks)

    assert model.encode.call_count == 2
    assert vector_store.upsert.call_count == 2


def test_first_batch_has_batch_size_chunks() -> None:
    n = BATCH_SIZE + 5
    chunks = _make_chunks(n)
    _, _, model = _call(chunks=chunks)

    first_call_texts = model.encode.call_args_list[0].args[0]
    second_call_texts = model.encode.call_args_list[1].args[0]
    assert len(first_call_texts) == BATCH_SIZE
    assert len(second_call_texts) == 5


def test_batch_payloads_reference_correct_chunks() -> None:
    n = BATCH_SIZE + 3
    doc_id = uuid.uuid4()
    chunks = _make_chunks(n, doc_id)
    _, vector_store, _ = _call(chunks=chunks, document_id=doc_id)

    first_payloads = vector_store.upsert.call_args_list[0].kwargs["payloads"]
    second_payloads = vector_store.upsert.call_args_list[1].kwargs["payloads"]

    assert [p["chunk_id"] for p in first_payloads] == [str(c.id) for c in chunks[:BATCH_SIZE]]
    assert [p["chunk_id"] for p in second_payloads] == [str(c.id) for c in chunks[BATCH_SIZE:]]


# --- chunk status + target finalization ---

def test_marks_embedded_chunks_and_attempts_target_finalization() -> None:
    # Chunk-status writes and target finalization are unconditional (not
    # gated behind pipeline_id) — the target's own status machine must stay
    # correct even for direct/untracked embed calls.
    doc_id = uuid.uuid4()
    chunks = _make_chunks(2, doc_id)

    store, _, _ = _call(chunks=chunks, document_id=doc_id, pipeline_id=None)

    uow = uow_of(store)
    uow.mark_chunks_embedded.assert_called_once_with([c.id for c in chunks])
    uow.finalize_target_if_all_chunks_embedded.assert_called_once_with(doc_id)


def test_empty_chunk_list_skips_marking_and_finalizing() -> None:
    store, _, _ = _call(chunks=[], pipeline_id=None)
    store.unit_of_work.assert_not_called()


# --- pipeline status tracking ---

def test_pipeline_id_emits_tracker_event_and_increments_counter() -> None:
    doc_id = uuid.uuid4()
    chunks = _make_chunks(2, doc_id)
    pipeline_id = str(uuid.uuid4())

    store, _, _ = _call(chunks=chunks, document_id=doc_id, pipeline_id=pipeline_id)

    uow = uow_of(store)
    tracker_events = outbox_for_queue(uow, TRACK_PIPELINE_STATUS_QUEUE)
    assert len(tracker_events) == 1
    assert tracker_events[0].payload["pipeline_id"] == pipeline_id
    assert tracker_events[0].dedup_key == (
        f"track:{pipeline_id}:embed:{doc_id}:{chunks[0].id}"
    )

    # add_outbox on a plain MagicMock returns a MagicMock (truthy), so the
    # newly-inserted branch runs and increments the counter by exactly one
    # batch, regardless of how many chunks/sub-batches the batch contained.
    uow.increment_embeddings_completed.assert_called_once_with(
        uuid.UUID(pipeline_id), 1
    )


def test_pipeline_id_emits_exactly_one_tracker_event_across_sub_batches() -> None:
    # A single embed_chunks message re-splits into BATCH_SIZE sub-batches for
    # encoding, but is still exactly one "batch" for scheduling purposes.
    n = BATCH_SIZE + 5
    doc_id = uuid.uuid4()
    chunks = _make_chunks(n, doc_id)
    pipeline_id = str(uuid.uuid4())

    store, _, _ = _call(chunks=chunks, document_id=doc_id, pipeline_id=pipeline_id)

    uow = uow_of(store)
    tracker_events = outbox_for_queue(uow, TRACK_PIPELINE_STATUS_QUEUE)
    assert len(tracker_events) == 1


def test_no_pipeline_id_skips_tracking_entirely() -> None:
    # Chunks are still marked embedded (see test_marks_embedded_chunks_...
    # above), but no tracker event/counter is written without a pipeline_id.
    chunks = _make_chunks(2)
    store, _, _ = _call(chunks=chunks, pipeline_id=None)

    uow = uow_of(store)
    assert outbox_for_queue(uow, TRACK_PIPELINE_STATUS_QUEUE) == []
    uow.increment_embeddings_completed.assert_not_called()


def test_redelivered_batch_does_not_double_count() -> None:
    # A redelivered message finds its tracker event already present:
    # add_outbox returns False, so the counter must not be incremented again.
    doc_id = uuid.uuid4()
    chunks = _make_chunks(2, doc_id)
    pipeline_id = str(uuid.uuid4())

    store = _make_store(chunks)
    uow = uow_of(store)
    uow.add_outbox.return_value = False
    vector_store = _make_vector_store()
    model = _make_model()

    _embed_chunks(
        document_id=str(doc_id),
        chunk_ids=[str(c.id) for c in chunks],
        store=store,
        vector_store=vector_store,
        model=model,
        model_size=4,
        pipeline_id=pipeline_id,
    )

    uow.increment_embeddings_completed.assert_not_called()
