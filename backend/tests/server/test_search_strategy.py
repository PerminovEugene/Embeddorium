"""Tests for the ``/search`` retrieval-strategy selection.

Covers the pure RRF fusion helper, ``searchMethod`` parsing, and the strategy
dispatch inside ``search_db`` (with the vector store / repo / embedder mocked,
mirroring the no-live-DB style of ``test_search_history``).
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from backend.server.search import service
from backend.server.search.schemas import SearchRequest
from backend.server.search.service import (
    parse_strategy,
    reciprocal_rank_fusion,
    search_db,
)
from backend.shared.clients import http_rerank_client
from backend.shared.models import Provider, SearchInput

# --------------------------------------------------------------------------- #
# reciprocal_rank_fusion (pure)                                               #
# --------------------------------------------------------------------------- #


def test_rrf_single_list_preserves_order():
    fused = reciprocal_rank_fusion([["a", "b", "c"]], k=60)
    assert [item_id for item_id, _ in fused] == ["a", "b", "c"]
    # 1 / (k + rank), rank is 1-based.
    assert fused[0][1] == pytest.approx(1 / 61)
    assert fused[1][1] == pytest.approx(1 / 62)


def test_rrf_overlapping_ids_sum_contributions():
    # "b" is rank 2 in the first list and rank 1 in the second, so it should
    # outrank "a" (rank 1 only in the first list) once contributions are summed.
    dense = ["a", "b", "c"]
    sparse = ["b", "x", "y"]
    fused = reciprocal_rank_fusion([dense, sparse], k=60)
    order = [item_id for item_id, _ in fused]
    assert order[0] == "b"
    b_score = dict(fused)["b"]
    assert b_score == pytest.approx(1 / 62 + 1 / 61)


def test_rrf_disjoint_lists_keep_all_ids():
    fused = reciprocal_rank_fusion([["a"], ["b"]], k=60)
    ids = {item_id for item_id, _ in fused}
    assert ids == {"a", "b"}
    # Equal rank (both rank 1) -> equal score -> deterministic id tie-break.
    assert [item_id for item_id, _ in fused] == ["a", "b"]


def test_rrf_k_flattens_weight_gap():
    small_k = reciprocal_rank_fusion([["a", "b"]], k=1)
    large_k = reciprocal_rank_fusion([["a", "b"]], k=1000)
    gap_small = dict(small_k)["a"] - dict(small_k)["b"]
    gap_large = dict(large_k)["a"] - dict(large_k)["b"]
    assert gap_large < gap_small


# --------------------------------------------------------------------------- #
# parse_strategy                                                              #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("value", [None, ""])
def test_parse_strategy_defaults_to_semantic(value):
    assert parse_strategy(value) == "semantic"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("semantic", "semantic"),
        ("keyword", "keyword"),
        ("hybrid", "hybrid"),
        ("embedding", "semantic"),  # legacy alias
        ("HYBRID", "hybrid"),  # case-insensitive
        ("  keyword ", "keyword"),
    ],
)
def test_parse_strategy_accepts_known(value, expected):
    assert parse_strategy(value) == expected


@pytest.mark.parametrize("value", ["dense", "bm25", "nonsense", 5, ["hybrid"]])
def test_parse_strategy_rejects_unknown(value):
    assert parse_strategy(value) is None


# --------------------------------------------------------------------------- #
# search_db dispatch                                                          #
# --------------------------------------------------------------------------- #

_RUN_ID = uuid.uuid4()
_CHUNK_ID = uuid.uuid4()
_DOC_ID = uuid.uuid4()


def _make_run() -> SimpleNamespace:
    return SimpleNamespace(
        id=_RUN_ID,
        dataset={"name": "docs-dataset"},
        actor_configs={
            "vector_store": {"collection": "col-a"},
            "embed_chunks": {"provider": {"provider_type": "mock", "model": "m1"}},
        },
    )


def _make_chunk() -> SimpleNamespace:
    return SimpleNamespace(
        id=_CHUNK_ID,
        document_id=_DOC_ID,
        chunk_index=3,
        text="chunk body",
        document=SimpleNamespace(source_url="http://example/doc"),
    )


def _make_store() -> MagicMock:
    store = MagicMock()
    store.chunks.get_many.return_value = [_make_chunk()]
    store.chunks.search_bm25.return_value = [(_make_chunk(), -1.5)]
    store.search_inputs.create.return_value = SearchInput(id=uuid.uuid4(), text="q")
    return store


def _request(method: str | None) -> SearchRequest:
    cfg: dict = {"runId": str(_RUN_ID), "topK": 5}
    if method is not None:
        cfg["searchMethod"] = method
    return SearchRequest(
        configuration=cfg,
        source={"inputs": [{"id": "q1", "text": "hello"}]},
    )


def _patch_common(monkeypatch, dense_hits=None):
    monkeypatch.setattr(service, "get_pipeline_run", lambda store, run_id: _make_run())

    async def _fake_embeddings(*args, **kwargs):
        return [[0.1, 0.2]]

    monkeypatch.setattr(service, "get_embeddings", _fake_embeddings)

    fake_store = MagicMock()
    fake_store.search.return_value = dense_hits if dense_hits is not None else []
    monkeypatch.setattr(service, "VectorStore", lambda **kwargs: fake_store)
    return fake_store


def _persisted_method(store: MagicMock) -> str:
    saved = store.searches.create.call_args.args[0]
    return saved.search_config["search_method"]


def test_unknown_strategy_returns_error(monkeypatch):
    called = MagicMock()
    monkeypatch.setattr(service, "get_pipeline_run", called)
    store = _make_store()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(search_db(store, MagicMock(), _request("dense")))

    assert exc.value.status_code == 400
    assert "search strategy" in exc.value.detail.lower()
    # Rejected before the run is even loaded.
    called.assert_not_called()


def test_semantic_strategy_uses_dense_only(monkeypatch):
    store = _make_store()
    dense_hits = [
        {
            "score": 0.9,
            "chunk_id": str(_CHUNK_ID),
            "document_id": str(_DOC_ID),
            "chunk_index": 3,
        }
    ]
    fake_store = _patch_common(monkeypatch, dense_hits=dense_hits)

    result = asyncio.run(search_db(store, MagicMock(), _request("semantic")))

    assert result["status"] == "success"
    [hit] = result["results"]
    assert hit["score"] == 0.9
    assert hit["chunkId"] == str(_CHUNK_ID)
    assert hit["chunkText"] == "chunk body"
    fake_store.search.assert_called_once()
    store.chunks.search_bm25.assert_not_called()
    assert _persisted_method(store) == "semantic"


def test_embedding_alias_routes_to_semantic(monkeypatch):
    store = _make_store()
    _patch_common(monkeypatch, dense_hits=[])

    result = asyncio.run(search_db(store, MagicMock(), _request("embedding")))

    assert result["status"] == "success"
    assert _persisted_method(store) == "semantic"


def test_keyword_strategy_uses_bm25_only(monkeypatch):
    store = _make_store()
    fake_embeddings = MagicMock()
    monkeypatch.setattr(service, "get_pipeline_run", lambda s, r: _make_run())
    monkeypatch.setattr(service, "get_embeddings", fake_embeddings)
    # VectorStore must never be constructed for keyword search.
    monkeypatch.setattr(
        service,
        "VectorStore",
        MagicMock(side_effect=AssertionError("dense path used for keyword")),
    )

    result = asyncio.run(search_db(store, MagicMock(), _request("keyword")))

    assert result["status"] == "success"
    [hit] = result["results"]
    assert hit["score"] == -1.5
    assert hit["chunkId"] == str(_CHUNK_ID)
    assert hit["chunkText"] == "chunk body"
    fake_embeddings.assert_not_called()
    store.chunks.search_bm25.assert_called_once()
    # Scoped to the selected run (as the string pipeline_id, matching the dense
    # path so both halves are filtered on the same value).
    assert store.chunks.search_bm25.call_args.kwargs["pipeline_id"] == str(_RUN_ID)
    assert _persisted_method(store) == "keyword"


def test_hybrid_strategy_fuses_both_signals(monkeypatch):
    store = _make_store()
    dense_hits = [
        {
            "score": 0.9,
            "chunk_id": str(_CHUNK_ID),
            "document_id": str(_DOC_ID),
            "chunk_index": 3,
        }
    ]
    fake_store = _patch_common(monkeypatch, dense_hits=dense_hits)

    result = asyncio.run(search_db(store, MagicMock(), _request("hybrid")))

    assert result["status"] == "success"
    [hit] = result["results"]
    # Same chunk from both halves -> fused score is the sum of both rank-1
    # contributions (1 / (60 + 1) twice).
    assert hit["score"] == pytest.approx(2 / 61)
    assert hit["chunkId"] == str(_CHUNK_ID)
    fake_store.search.assert_called_once()
    # The dense (Qdrant) half must be scoped with the *string* pipeline_id:
    # Qdrant's MatchValue rejects a raw uuid.UUID, so passing run.id here used to
    # raise a ValidationError at runtime.
    assert fake_store.search.call_args.kwargs["pipeline_id"] == str(_RUN_ID)
    assert isinstance(fake_store.search.call_args.kwargs["pipeline_id"], str)
    store.chunks.search_bm25.assert_called_once()
    assert store.chunks.search_bm25.call_args.kwargs["pipeline_id"] == str(_RUN_ID)
    assert _persisted_method(store) == "hybrid"


# --------------------------------------------------------------------------- #
# hybrid + cross-encoder reranking                                            #
# --------------------------------------------------------------------------- #

_RERANKER_ID = uuid.uuid4()


class _FakeReranker:
    """Stand-in for HttpRerankClient — no network, scores by text length."""

    def __init__(self, model, base_url, api_key=None, path=None):
        self.model = model
        self.base_url = base_url
        self.path = path

    def rerank(self, query, texts):
        # Deterministic, text-derived scores so the test can assert reordering.
        return [float(len(text)) for text in texts]


def _persisted_config(store: MagicMock) -> dict:
    return store.searches.create.call_args.args[0].search_config


def _rerank_request(**overrides) -> SearchRequest:
    cfg: dict = {
        "runId": str(_RUN_ID),
        "topK": 5,
        "searchMethod": "hybrid",
        "useReranking": True,
        "rerankerProviderId": str(_RERANKER_ID),
        "rerankerTopK": 1,
    }
    cfg.update(overrides)
    return SearchRequest(
        configuration=cfg,
        source={"inputs": [{"id": "q1", "text": "hello"}]},
    )


def _cross_encoder_provider() -> Provider:
    return Provider(
        id=_RERANKER_ID,
        name="reranker",
        provider_type="ollama",
        model_type="cross-encoder",
        config={},
    )


def test_hybrid_reranking_applies_and_records_marker(monkeypatch):
    store = _make_store()
    store.providers.get.return_value = _cross_encoder_provider()
    dense_hits = [
        {
            "score": 0.9,
            "chunk_id": str(_CHUNK_ID),
            "document_id": str(_DOC_ID),
            "chunk_index": 3,
        }
    ]
    _patch_common(monkeypatch, dense_hits=dense_hits)
    monkeypatch.setattr(http_rerank_client, "HttpRerankClient", _FakeReranker)

    result = asyncio.run(search_db(store, MagicMock(), _rerank_request()))

    assert result["status"] == "success"
    [hit] = result["results"]
    # Score overwritten with the cross-encoder score (len("chunk body") == 10).
    assert hit["score"] == float(len("chunk body"))
    config = _persisted_config(store)
    assert config["search_method"] == "hybrid"
    assert config["reranked"] is True
    assert config["reranker_provider_id"] == str(_RERANKER_ID)
    assert config["reranker_top_k"] == 1


def test_hybrid_reranking_degrades_on_client_failure(monkeypatch):
    store = _make_store()
    store.providers.get.return_value = _cross_encoder_provider()
    dense_hits = [
        {
            "score": 0.9,
            "chunk_id": str(_CHUNK_ID),
            "document_id": str(_DOC_ID),
            "chunk_index": 3,
        }
    ]
    _patch_common(monkeypatch, dense_hits=dense_hits)

    def _boom(*args, **kwargs):
        raise RuntimeError("model download failed")

    monkeypatch.setattr(http_rerank_client, "HttpRerankClient", _boom)

    result = asyncio.run(search_db(store, MagicMock(), _rerank_request()))

    # Reranking failure degrades to the original fused results, not an error.
    assert result["status"] == "success"
    [hit] = result["results"]
    assert hit["score"] == pytest.approx(2 / 61)  # original RRF score preserved


def test_hybrid_reranking_requires_provider_id(monkeypatch):
    store = _make_store()
    _patch_common(monkeypatch, dense_hits=[])

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            search_db(store, MagicMock(), _rerank_request(rerankerProviderId=""))
        )

    assert exc.value.status_code == 400
    assert "rerankerProviderId" in exc.value.detail
    store.searches.create.assert_not_called()


def test_hybrid_reranking_requires_valid_top_k(monkeypatch):
    store = _make_store()
    store.providers.get.return_value = _cross_encoder_provider()
    _patch_common(monkeypatch, dense_hits=[])

    with pytest.raises(HTTPException) as exc:
        asyncio.run(search_db(store, MagicMock(), _rerank_request(rerankerTopK=0)))

    assert exc.value.status_code == 400
    assert "rerankerTopK" in exc.value.detail


def test_hybrid_reranking_rejects_non_cross_encoder_provider(monkeypatch):
    store = _make_store()
    store.providers.get.return_value = Provider(
        id=_RERANKER_ID,
        name="embedder",
        provider_type="mock",
        model_type="embedding",
        config={},
    )
    _patch_common(monkeypatch, dense_hits=[])

    with pytest.raises(HTTPException) as exc:
        asyncio.run(search_db(store, MagicMock(), _rerank_request()))

    assert exc.value.status_code == 400
    assert "cross-encoder" in exc.value.detail.lower()


def test_reranking_ignored_for_non_hybrid_strategy(monkeypatch):
    store = _make_store()
    _patch_common(monkeypatch, dense_hits=[])

    # useReranking on a semantic search is a no-op: no provider lookup, no marker.
    result = asyncio.run(
        search_db(store, MagicMock(), _rerank_request(searchMethod="semantic"))
    )

    assert result["status"] == "success"
    store.providers.get.assert_not_called()
    assert "reranked" not in _persisted_config(store)
