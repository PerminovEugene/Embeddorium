"""Tests for the ``/searches`` history endpoints.

Uses FastAPI's TestClient against the real router (no live DB): the shared
``SqlStore`` is supplied via a ``get_sql_store`` dependency override so every
handler receives a MagicMock store.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.server.dependencies import get_sql_store
from backend.server.search.router import router
from backend.shared.models import PipelineRun, Search, SearchInput

_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)


@contextmanager
def _override_store(store: MagicMock):
    """Inject *store* as the shared ``SqlStore`` for the duration of a request."""
    _app.dependency_overrides[get_sql_store] = lambda: store
    try:
        yield
    finally:
        _app.dependency_overrides.pop(get_sql_store, None)

_SEARCH_ID = uuid.uuid4()
_RUN_ID = uuid.uuid4()
_INPUT_ID = uuid.uuid4()


def _make_run() -> PipelineRun:
    return PipelineRun(
        id=_RUN_ID,
        name="run-a",
        dataset={"name": "docs-dataset", "source_type": "web"},
        actor_configs={},
        status="completed",
    )


def _make_search(results: list[dict] | None = None) -> Search:
    return Search(
        id=_SEARCH_ID,
        pipeline_id=_RUN_ID,
        user_input_id=_INPUT_ID,
        search_config={"top_n": 5, "search_method": "embedding"},
        results=results if results is not None else [{"chunkId": "c1", "score": 0.9}],
        created_at=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
    )


def _mock_store(search: Search | None) -> MagicMock:
    store = MagicMock()
    store.searches.list_recent.return_value = [search] if search else []
    store.searches.get.return_value = search
    store.search_inputs.get.return_value = SearchInput(id=_INPUT_ID, text="my query")
    store.pipeline_runs.get.return_value = _make_run()
    return store


def test_list_searches_joins_run_and_input_info():
    """GET /searches returns camelCase summaries with run name, dataset name
    and input text joined in, and counts results without inlining them."""
    with _override_store(_mock_store(_make_search())):
        res = client.get("/searches")

    assert res.status_code == 200
    [item] = res.json()
    assert item["id"] == str(_SEARCH_ID)
    assert item["pipelineId"] == str(_RUN_ID)
    assert item["runName"] == "run-a"
    assert item["datasetName"] == "docs-dataset"
    assert item["inputText"] == "my query"
    assert item["topK"] == 5
    assert item["searchMethod"] == "embedding"
    assert item["resultCount"] == 1
    assert "results" not in item


def test_get_search_returns_stored_results_in_order():
    """GET /searches/{id} includes the stored hits verbatim, preserving the
    persisted (score-sorted) order so index == rank."""
    hits = [{"chunkId": "c1", "score": 0.9}, {"chunkId": "c2", "score": 0.5}]
    with _override_store(_mock_store(_make_search(results=hits))):
        res = client.get(f"/searches/{_SEARCH_ID}")

    assert res.status_code == 200
    body = res.json()
    assert body["results"] == hits
    assert body["resultCount"] == 2


def test_get_unknown_search_returns_404():
    """GET /searches/{id} 404s when the id has no persisted search."""
    with _override_store(_mock_store(None)):
        res = client.get(f"/searches/{uuid.uuid4()}")

    assert res.status_code == 404
