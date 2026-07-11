"""Tests for the /pipeline-runs endpoints.

Uses FastAPI's TestClient against the real router (no live DB or broker):
- The shared ``SqlStore`` is supplied via a ``get_sql_store`` dependency
  override, so every handler receives a MagicMock store. The ``get_broker``
  dependency (used by the launch handler) is overridden with a MagicMock too.
- ``seed_pipeline`` is patched at its import site in ``pipeline.router`` so
  broker setup is skipped.

Each test exercises exactly one behaviour; see the docstring for the rule
under test.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.server.dependencies import get_broker, get_sql_store
from backend.server.pipeline.router import router
from backend.shared.models import MockProvider, PipelineRun, WebDataset

# ---------------------------------------------------------------------------
# Test app + client
# ---------------------------------------------------------------------------

_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)


@contextmanager
def _override_store(store: MagicMock):
    """Inject *store* as the shared ``SqlStore`` (plus a stub broker) for the
    duration of a request."""
    _app.dependency_overrides[get_sql_store] = lambda: store
    _app.dependency_overrides[get_broker] = lambda: MagicMock()
    try:
        yield
    finally:
        _app.dependency_overrides.pop(get_sql_store, None)
        _app.dependency_overrides.pop(get_broker, None)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_RUN_ID = uuid.uuid4()
_DATASET_ID = uuid.uuid4()
_PROVIDER_ID = uuid.uuid4()


def _make_dataset() -> WebDataset:
    return WebDataset(
        id=_DATASET_ID,
        name="test-dataset",
        source_type="web",
        url="https://example.com",
        process_child_links=False,
        process_cross_domain_links=False,
        depth=1,
    )


def _make_provider() -> MockProvider:
    return MockProvider(
        id=_PROVIDER_ID,
        name="mock-embed",
        model_type="embedding",
        provider_type="mock",
    )


def _make_run(status: str = "pending") -> PipelineRun:
    """Minimal PipelineRun domain object suitable for all route tests."""
    return PipelineRun(
        id=_RUN_ID,
        dataset={
            "name": "test-dataset",
            "source_type": "web",
            "url": "https://example.com",
        },
        actor_configs={
            "chunk_document": {
                "chunker": "text_markdown",
                "settings": {"chunk_size": 1200, "chunk_overlap": 150},
            },
            "vector_store": {"collection": "test-dataset", "similarity": "cosine"},
            "embed_chunks": {
                "provider": {"provider_type": "mock", "name": "mock-embed"},
            },
        },
        status=status,
        started_at=None,
        finished_at=None,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_store(
    *,
    dataset: Optional[Any] = None,
    provider: Optional[Any] = None,
    run: Optional[PipelineRun] = None,
    created_run: Optional[PipelineRun] = None,
    updated_run: Optional[PipelineRun] = None,
    deleted: bool = True,
) -> MagicMock:
    """Build a MagicMock SqlStore wired with the given return values."""
    store = MagicMock()
    store.datasets.get.return_value = dataset
    store.providers.get.return_value = provider
    store.pipeline_runs.get.return_value = run
    store.pipeline_runs.create.return_value = created_run or run
    store.pipeline_runs.update_status.return_value = updated_run or run
    store.pipeline_runs.delete.return_value = deleted
    store.pipeline_runs.list_recent.return_value = [run] if run else []
    return store


# Standard valid create payload — the provider id lives inside
# actorSettings.embed_chunks under the plugin field key "provider".
_CREATE_PAYLOAD: Dict[str, Any] = {
    "datasetId": str(_DATASET_ID),
    "actorSettings": {"embed_chunks": {"provider": str(_PROVIDER_ID)}},
}

# ---------------------------------------------------------------------------
# POST /pipeline-runs  — create
# ---------------------------------------------------------------------------


def test_create_returns_pending_run_and_does_not_call_seed_pipeline() -> None:
    """Creating a run persists it as pending and does NOT launch seed messages."""
    pending_run = _make_run("pending")
    store_mock = _make_store(
        dataset=_make_dataset(),
        provider=_make_provider(),
        run=pending_run,
        created_run=pending_run,
    )
    with _override_store(store_mock):
        with patch("backend.server.pipeline.router.seed_pipeline") as mock_seed:
            resp = client.post("/pipeline-runs", json=_CREATE_PAYLOAD)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["id"] == str(_RUN_ID)

    # seed_pipeline must NOT have been called during creation.
    mock_seed.assert_not_called()

    # The store was used (create was called once).
    store_mock.pipeline_runs.create.assert_called_once()


def test_create_persists_full_actor_settings_snapshot() -> None:
    """Every per-actor block from the form is resolved and stored on the run."""
    pending_run = _make_run("pending")
    store_mock = _make_store(
        dataset=_make_dataset(),
        provider=_make_provider(),
        run=pending_run,
        created_run=pending_run,
    )
    payload = {
        "datasetId": str(_DATASET_ID),
        "actorSettings": {
            "chunk_document": {
                "chunker": "text_section",
                "settings": {"chunk_size": 800, "chunk_overlap": 80},
            },
            "embed_chunks": {"provider": str(_PROVIDER_ID), "similarity": "dot"},
            "parse_source": {"parser": "html"},
            "schedule_embeddings": {"batchSize": 16},
            "validate_source": {"normalizeUrls": False, "dedup": False},
            "schedule_discovered_links": {"followChildLinks": False},
            "fetch_source": {"verifyTls": False, "timeoutSeconds": 12, "fileGlob": "*.html"},
            "filter_documents": {"enabled": False, "keywords": "vat, customs"},
        },
    }
    with _override_store(store_mock):
        with patch("backend.server.pipeline.router.seed_pipeline"):
            resp = client.post("/pipeline-runs", json=payload)

    assert resp.status_code == 200, resp.text

    created_run = store_mock.pipeline_runs.create.call_args[0][0]
    cfg = created_run.actor_configs
    # The chunk_document block is stored verbatim: {chunker, settings}.
    assert cfg["chunk_document"] == {
        "chunker": "text_section",
        "settings": {"chunk_size": 800, "chunk_overlap": 80},
    }
    assert cfg["vector_store"]["similarity"] == "dot"
    assert cfg["parse_source"]["parser"] == "html"
    assert cfg["schedule_embeddings"]["batch_size"] == 16
    assert cfg["fetch_source"]["verify_tls"] is False
    assert cfg["fetch_source"]["timeout_seconds"] == 12
    assert cfg["validate_source"]["normalize_urls"] is False
    assert cfg["validate_source"]["dedup"] is False
    assert cfg["schedule_discovered_links"]["follow_child_links"] is False
    assert cfg["fetch_source"]["file_glob"] == "*.html"
    assert cfg["filter_documents"] == {"enabled": False, "keywords": "vat, customs"}


def test_create_accepts_legacy_actor_settings_keys() -> None:
    """Pre-merge UI builds send crawl_frontier_manager / fetch_file_source
    blocks and the legacy embed_chunks.providerId key; those map onto
    validate_source / fetch_source / embed_chunks.provider."""
    pending_run = _make_run("pending")
    store_mock = _make_store(
        dataset=_make_dataset(),
        provider=_make_provider(),
        run=pending_run,
        created_run=pending_run,
    )
    payload = {
        "datasetId": str(_DATASET_ID),
        "actorSettings": {
            "embed_chunks": {"providerId": str(_PROVIDER_ID)},
            "crawl_frontier_manager": {"normalizeUrls": False},
            "fetch_file_source": {"glob": "*.html", "dedup": False},
        },
    }
    with _override_store(store_mock):
        with patch("backend.server.pipeline.router.seed_pipeline"):
            resp = client.post("/pipeline-runs", json=payload)

    assert resp.status_code == 200, resp.text
    cfg = store_mock.pipeline_runs.create.call_args[0][0].actor_configs
    assert cfg["validate_source"]["normalize_urls"] is False
    # Legacy fetch_file_source.dedup feeds the merged validate_source gate...
    assert cfg["validate_source"]["dedup"] is False
    # ...and its glob becomes the merged fetch_source file_glob.
    assert cfg["fetch_source"]["file_glob"] == "*.html"


def test_create_omitted_actor_blocks_fall_back_to_defaults() -> None:
    """A minimal payload still yields a fully-resolved, default-filled snapshot."""
    pending_run = _make_run("pending")
    store_mock = _make_store(
        dataset=_make_dataset(),
        provider=_make_provider(),
        run=pending_run,
        created_run=pending_run,
    )
    with _override_store(store_mock):
        with patch("backend.server.pipeline.router.seed_pipeline"):
            resp = client.post("/pipeline-runs", json=_CREATE_PAYLOAD)

    assert resp.status_code == 200, resp.text
    cfg = store_mock.pipeline_runs.create.call_args[0][0].actor_configs
    assert cfg["fetch_source"]["verify_tls"] is True
    assert cfg["schedule_embeddings"]["batch_size"] == 32
    assert cfg["filter_documents"]["enabled"] is True


def test_create_400_when_provider_id_missing() -> None:
    """Returns 400 when embed_chunks.provider is absent."""
    store_mock = _make_store(dataset=_make_dataset(), provider=_make_provider())
    with _override_store(store_mock):
        resp = client.post(
            "/pipeline-runs",
            json={"datasetId": str(_DATASET_ID), "actorSettings": {}},
        )

    assert resp.status_code == 400
    assert "provider" in resp.json()["detail"]


def test_create_404_when_dataset_missing() -> None:
    """Returns 404 when the dataset doesn't exist."""
    store_mock = _make_store(dataset=None, provider=_make_provider())
    with _override_store(store_mock):
        resp = client.post("/pipeline-runs", json=_CREATE_PAYLOAD)

    assert resp.status_code == 404
    assert "Dataset" in resp.json()["detail"]


def test_create_404_when_provider_missing() -> None:
    """Returns 404 when the provider doesn't exist."""
    store_mock = _make_store(dataset=_make_dataset(), provider=None)
    with _override_store(store_mock):
        resp = client.post("/pipeline-runs", json=_CREATE_PAYLOAD)

    assert resp.status_code == 404
    assert "Provider" in resp.json()["detail"]


def test_create_400_when_provider_not_embedding() -> None:
    """Returns 400 when the provider's model_type is not 'embedding'."""
    text_provider = MockProvider(
        id=_PROVIDER_ID,
        name="text-model",
        model_type="text",
        provider_type="mock",
    )
    store_mock = _make_store(dataset=_make_dataset(), provider=text_provider)
    with _override_store(store_mock):
        resp = client.post("/pipeline-runs", json=_CREATE_PAYLOAD)

    assert resp.status_code == 400
    assert "embedding" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /pipeline-runs/{id}/launch — launch / relaunch
# ---------------------------------------------------------------------------


def test_launch_pending_run_calls_seed_pipeline_and_transitions_to_running() -> None:
    """Launching a pending run calls seed_pipeline once and advances to running."""
    pending_run = _make_run("pending")
    running_run = _make_run("running")
    store_mock = _make_store(run=pending_run, updated_run=running_run)

    with _override_store(store_mock):
        with patch("backend.server.pipeline.router.seed_pipeline") as mock_seed:
            resp = client.post("/pipeline-runs/{}/launch".format(_RUN_ID))

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "running"

    mock_seed.assert_called_once()

    # update_status must be called with status="running" and reset_finished=True.
    store_mock.pipeline_runs.update_status.assert_called_once()
    call_kwargs = store_mock.pipeline_runs.update_status.call_args
    assert call_kwargs[0][1] == "running"
    assert call_kwargs[1].get("reset_finished") is True


def test_launch_running_run_returns_409_and_does_not_call_seed() -> None:
    """Launching a run that is already running returns 409 without seeding."""
    running_run = _make_run("running")
    store_mock = _make_store(run=running_run)

    with _override_store(store_mock):
        with patch("backend.server.pipeline.router.seed_pipeline") as mock_seed:
            resp = client.post("/pipeline-runs/{}/launch".format(_RUN_ID))

    assert resp.status_code == 409
    assert "already running" in resp.json()["detail"]
    mock_seed.assert_not_called()


def test_launch_failed_run_is_allowed_relaunch() -> None:
    """Launching a failed run is permitted (relaunch path)."""
    failed_run = _make_run("failed")
    running_run = _make_run("running")
    store_mock = _make_store(run=failed_run, updated_run=running_run)

    with _override_store(store_mock):
        with patch("backend.server.pipeline.router.seed_pipeline") as mock_seed:
            resp = client.post("/pipeline-runs/{}/launch".format(_RUN_ID))

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "running"
    mock_seed.assert_called_once()


def test_launch_completed_run_is_allowed_relaunch() -> None:
    """Launching a completed run is permitted (relaunch path)."""
    completed_run = _make_run("completed")
    running_run = _make_run("running")
    store_mock = _make_store(run=completed_run, updated_run=running_run)

    with _override_store(store_mock):
        with patch("backend.server.pipeline.router.seed_pipeline") as mock_seed:
            resp = client.post("/pipeline-runs/{}/launch".format(_RUN_ID))

    assert resp.status_code == 200, resp.text
    mock_seed.assert_called_once()


def test_launch_returns_404_when_run_not_found() -> None:
    """Returns 404 when the run id doesn't exist."""
    store_mock = _make_store(run=None)

    with _override_store(store_mock):
        with patch("backend.server.pipeline.router.seed_pipeline"):
            resp = client.post("/pipeline-runs/{}/launch".format(_RUN_ID))

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /pipeline-runs/{id} — update status
# ---------------------------------------------------------------------------


def test_patch_status_to_failed_sets_finished_at() -> None:
    """PATCH to 'failed' calls update_status with a non-None finished_at."""
    pending_run = _make_run("pending")
    failed_run = _make_run("failed")
    store_mock = _make_store(run=pending_run, updated_run=failed_run)

    with _override_store(store_mock):
        resp = client.patch(
            "/pipeline-runs/{}".format(_RUN_ID),
            json={"status": "failed"},
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "failed"

    store_mock.pipeline_runs.update_status.assert_called_once()
    call_kwargs = store_mock.pipeline_runs.update_status.call_args
    assert call_kwargs[1].get("finished_at") is not None


def test_patch_status_to_completed_sets_finished_at() -> None:
    """PATCH to 'completed' calls update_status with a non-None finished_at."""
    pending_run = _make_run("pending")
    completed_run = _make_run("completed")
    store_mock = _make_store(run=pending_run, updated_run=completed_run)

    with _override_store(store_mock):
        resp = client.patch(
            "/pipeline-runs/{}".format(_RUN_ID),
            json={"status": "completed"},
        )

    assert resp.status_code == 200, resp.text
    call_kwargs = store_mock.pipeline_runs.update_status.call_args
    assert call_kwargs[1].get("finished_at") is not None


def test_patch_status_to_running_does_not_set_finished_at() -> None:
    """PATCH to 'running' does not set finished_at (non-terminal status)."""
    pending_run = _make_run("pending")
    running_run = _make_run("running")
    store_mock = _make_store(run=pending_run, updated_run=running_run)

    with _override_store(store_mock):
        resp = client.patch(
            "/pipeline-runs/{}".format(_RUN_ID),
            json={"status": "running"},
        )

    assert resp.status_code == 200, resp.text
    call_kwargs = store_mock.pipeline_runs.update_status.call_args
    assert call_kwargs[1].get("finished_at") is None


def test_patch_returns_404_when_run_not_found() -> None:
    """Returns 404 when the run id doesn't exist."""
    store_mock = _make_store(run=None)
    with _override_store(store_mock):
        resp = client.patch(
            "/pipeline-runs/{}".format(_RUN_ID),
            json={"status": "failed"},
        )

    assert resp.status_code == 404


def test_patch_returns_422_for_invalid_status() -> None:
    """Returns 422 when the requested status value is not a valid literal."""
    run = _make_run("pending")
    store_mock = _make_store(run=run)

    with _override_store(store_mock):
        resp = client.patch(
            "/pipeline-runs/{}".format(_RUN_ID),
            json={"status": "invalid-status"},
        )

    assert resp.status_code == 422
