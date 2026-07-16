"""Tests for embed_chunks strategy discovery
(backend.plugins.embed_chunks.registry)."""

from __future__ import annotations

import pytest

from backend.plugins.embed_chunks.registry import (
    DEFAULT_EMBED_STRATEGY,
    build_embed_strategy,
    get_embed_strategy_class,
    list_embed_strategy_configs,
)

_BUILTIN_NAMES = {"standard"}


def test_discovers_builtin_strategies():
    names = {cfg.name for cfg in list_embed_strategy_configs()}
    assert _BUILTIN_NAMES <= names


def test_configs_sorted_by_name():
    names = [cfg.name for cfg in list_embed_strategy_configs()]
    assert names == sorted(names)


def test_provider_field_uses_provider_id_type():
    cfg = get_embed_strategy_class(DEFAULT_EMBED_STRATEGY).config
    assert [f.key for f in cfg.fields] == ["provider"]
    field = cfg.fields[0]
    assert field.type == "provider_id"
    assert field.required is True


def test_unknown_name_raises_value_error():
    with pytest.raises(ValueError):
        get_embed_strategy_class("does_not_exist")


def test_ollama_snapshot_resolves_to_ollama_provider():
    strategy = build_embed_strategy(
        DEFAULT_EMBED_STRATEGY,
        {"provider": {"provider_type": "ollama", "model_name": "nomic-embed-text"}},
    )
    resolved = strategy.resolve()
    assert resolved.provider == "ollama"
    assert resolved.model == "nomic-embed-text"
    assert resolved.mock_dim is None


def test_mock_snapshot_resolves_to_mock_provider_with_dim():
    strategy = build_embed_strategy(
        DEFAULT_EMBED_STRATEGY,
        {"provider": {"provider_type": "mock", "mock_dim": 8}},
    )
    resolved = strategy.resolve()
    assert resolved.provider == "mock"
    assert resolved.model == "mock"
    assert resolved.mock_dim == 8


def test_openai_snapshot_resolves_to_openai_provider():
    strategy = build_embed_strategy(
        DEFAULT_EMBED_STRATEGY,
        {
            "provider": {
                "provider_type": "openai",
                "config": {
                    "url": "https://api.openai.test/v1",
                    "api_key": "secret",
                    "model_name": "text-embedding-3-small",
                },
            }
        },
    )
    resolved = strategy.resolve()
    assert resolved.provider == "openai"
    assert resolved.model == "text-embedding-3-small"
    assert resolved.mock_dim is None


def test_unknown_snapshot_raises():
    # The in-process HuggingFace fallback was removed: an unknown/legacy
    # provider type must raise rather than silently degrade to a local model.
    strategy = build_embed_strategy(
        DEFAULT_EMBED_STRATEGY,
        {
            "provider": {
                "provider_type": "some_legacy_type",
                "model_name": "text-embedding-3-small",
            }
        },
    )
    with pytest.raises(ValueError, match="Unknown provider type"):
        strategy.resolve()
