"""Tests for GET /actor-configs.

No DB/broker involved — the route only reads the in-process plugin registries.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.server.actor_configs.router import router

_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)


def _by_actor():
    resp = client.get("/actor-configs")
    assert resp.status_code == 200, resp.text
    return {entry["actor"]: entry for entry in resp.json()}


def test_lists_every_plugin_backed_actor():
    by_actor = _by_actor()
    assert {
        "validate_source",
        "fetch_source",
        "parse_source",
        "filter_documents",
        "chunk_document",
        "embed_chunks",
    } == set(by_actor)


def test_fetch_source_declares_web_and_local_strategies_with_fields():
    fetch = _by_actor()["fetch_source"]
    strategies = {s["name"]: s for s in fetch["strategies"]}
    assert {"web", "local"} <= set(strategies)

    web_field_keys = {f["key"] for f in strategies["web"]["fields"]}
    assert {"verify_tls", "timeout_seconds", "allowed_content_types"} <= web_field_keys

    # field keys stay snake_case; field-level object keys are camelCase.
    timeout = next(
        f for f in strategies["web"]["fields"] if f["key"] == "timeout_seconds"
    )
    assert set(timeout) == {
        "key", "label", "type", "default", "min", "max", "options",
        "placeholder", "required",
    }
    assert timeout["default"] == 30
    assert timeout["min"] == 1


def test_embed_chunks_provider_field_is_required_provider_id():
    embed = _by_actor()["embed_chunks"]
    standard = next(s for s in embed["strategies"] if s["name"] == "standard")
    provider = next(f for f in standard["fields"] if f["key"] == "provider")
    assert provider["type"] == "provider_id"
    assert provider["required"] is True


def test_chunk_document_strategies_are_the_discovered_chunkers():
    chunk = _by_actor()["chunk_document"]
    names = {s["name"] for s in chunk["strategies"]}
    assert {"text_markdown", "text_fixed"} <= names
