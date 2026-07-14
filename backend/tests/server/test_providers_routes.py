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


def test_provider_configs_expose_every_discovered_adapter() -> None:
    response = client.get("/providers/configs")

    assert response.status_code == 200
    configs = {item["name"]: item for item in response.json()}
    assert {"fastembed", "mock", "ollama", "openai", "cross_encoder"} <= set(configs)
    assert configs["fastembed"]["type"] == "builtin"
    assert configs["ollama"]["type"] == "remote"
    assert "embedding" in configs["ollama"]["supportedModelTypes"]
    assert any(field["key"] == "model_name" for field in configs["fastembed"]["fields"])
    cross_encoder = configs["cross_encoder"]
    assert cross_encoder["type"] == "remote"
    assert cross_encoder["supportedModelTypes"] == ["cross-encoder"]
    field_keys = {field["key"] for field in cross_encoder["fields"]}
    assert {"model_name", "url", "port"} <= field_keys


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
