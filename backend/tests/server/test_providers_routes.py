"""Provider CRUD metadata and validation routes."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.server.dependencies import get_sql_store
from backend.server.providers.router import router

app = FastAPI()
app.include_router(router)
store = MagicMock()
app.dependency_overrides[get_sql_store] = lambda: store
client = TestClient(app)


def test_provider_configs_expose_every_discovered_provider() -> None:
    response = client.get("/providers/configs")

    assert response.status_code == 200
    configs = {item["name"]: item for item in response.json()}
    assert set(configs) == {"mock", "ollama", "openai"}
    assert "cross_encoder" not in configs
    assert "fastembed" not in configs
    assert configs["mock"]["type"] == "builtin"
    assert configs["ollama"]["type"] == "remote"

    ollama = configs["ollama"]
    # Connection fields live at the provider level; the model to run is a
    # capability field under the matching model type.
    conn_keys = {field["key"] for field in ollama["fields"]}
    assert {"url", "port"} <= conn_keys
    assert "embedding" in ollama["supportedModelTypes"]
    assert "cross-encoder" in ollama["supportedModelTypes"]

    model_types = {mt["modelType"]: mt for mt in ollama["modelTypes"]}
    assert any(f["key"] == "model_name" for f in model_types["embedding"]["fields"])
    reranker_fields = {f["key"] for f in model_types["cross-encoder"]["fields"]}
    assert {"model_name", "rerank_path"} <= reranker_fields


def test_create_rejects_unknown_provider_type() -> None:
    response = client.post(
        "/providers",
        json={
            "name": "bad",
            "providerType": "missing",
            "modelType": "embedding",
            "config": {},
        },
    )

    assert response.status_code == 400
    assert "Unknown provider type" in response.json()["detail"]
    store.providers.create.assert_not_called()


def test_create_rejects_invalid_provider_config() -> None:
    response = client.post(
        "/providers",
        json={
            "name": "bad mock",
            "providerType": "mock",
            "modelType": "embedding",
            "config": {"mock_dim": 0},
        },
    )

    assert response.status_code == 400
    assert "at least 1" in response.json()["detail"]
