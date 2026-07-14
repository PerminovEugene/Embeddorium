"""Tests for GET /actor-configs.

No DB/broker involved — the route only reads the in-process plugin registries.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.plugins.chunkers.registry import list_chunker_configs
from backend.plugins.embed_chunks.registry import list_embed_strategy_configs
from backend.plugins.fetch_source.registry import list_fetch_strategy_configs
from backend.plugins.filter_documents.registry import list_filter_strategy_configs
from backend.plugins.parse_source.registry import list_parse_strategy_configs
from backend.plugins.validate_source.registry import list_validation_strategy_configs
from backend.server.actor_configs.router import router

_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)

# Actor -> its registry lister; the endpoint must expose exactly these, so the
# parity test below catches a missing ``_ACTOR_LISTERS`` entry or a dropped
# field just as well as a stale hardcoded expectation would.
_LISTERS = {
    "validate_source": list_validation_strategy_configs,
    "fetch_source": list_fetch_strategy_configs,
    "parse_source": list_parse_strategy_configs,
    "filter_documents": list_filter_strategy_configs,
    "chunk_document": list_chunker_configs,
    "embed_chunks": list_embed_strategy_configs,
}


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
    assert strategies["local"]["fields"] == []

    web_field_keys = {f["key"] for f in strategies["web"]["fields"]}
    assert {"verify_tls", "timeout_seconds", "allowed_content_types"} <= web_field_keys

    # field keys stay snake_case; field-level object keys are camelCase.
    timeout = next(
        f for f in strategies["web"]["fields"] if f["key"] == "timeout_seconds"
    )
    assert set(timeout) == {
        "key",
        "label",
        "type",
        "default",
        "min",
        "max",
        "options",
        "placeholder",
        "required",
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


@pytest.mark.parametrize("actor", sorted(_LISTERS))
def test_served_strategies_and_fields_match_the_registry(actor):
    """The endpoint must serialize every discovered strategy *and* every one of
    its fields — nothing dropped by ``_ACTOR_LISTERS`` gaps or camelCasing.

    Comparing the wire payload against the registry directly (rather than a
    hardcoded list) makes this the single guard for the whole
    "strategies + fields reach the UI" contract.
    """
    served = {
        s["name"]: [f["key"] for f in s["fields"]]
        for s in _by_actor()[actor]["strategies"]
    }
    expected = {cfg.name: [f.key for f in cfg.fields] for cfg in _LISTERS[actor]()}
    assert served == expected


def test_field_key_values_stay_snake_case_on_the_wire():
    """Object keys are camelCased, but a field's ``key`` *value* is the exact
    storage key and must round-trip verbatim (never camelCased)."""
    by_actor = _by_actor()

    def field_keys(actor: str, strategy: str) -> set[str]:
        strat = next(s for s in by_actor[actor]["strategies"] if s["name"] == strategy)
        return {f["key"] for f in strat["fields"]}

    assert {"verify_tls", "timeout_seconds", "allowed_content_types"} <= field_keys(
        "fetch_source", "web"
    )
    assert {"chunk_overlap"} <= field_keys("chunk_document", "text_markdown")
