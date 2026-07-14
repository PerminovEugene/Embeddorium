"""Provider adapter discovery, defaults, and target resolution."""

from __future__ import annotations

import pytest

from backend.plugins.provider_types.registry import (
    list_provider_type_configs,
    resolve_embed_target,
    resolve_rerank_target,
    validate_provider,
)


def test_registry_discovers_builtin_adapters() -> None:
    configs = {config.name: config for config in list_provider_type_configs()}
    assert {"fastembed", "mock", "ollama", "openai", "cross_encoder"} <= set(configs)
    assert configs["mock"].type == "builtin"
    assert configs["openai"].type == "remote"
    assert configs["cross_encoder"].type == "remote"
    assert configs["cross_encoder"].supported_model_types == ("cross-encoder",)


def test_validate_provider_resolves_defaults_and_drops_unknown_keys() -> None:
    config = validate_provider(
        "fastembed",
        "embedding",
        {"unknown": "ignored"},
    )
    assert config == {"model_name": "BAAI/bge-small-en-v1.5"}


def test_validate_provider_rejects_wrong_model_type() -> None:
    with pytest.raises(ValueError, match="does not support"):
        validate_provider("mock", "text", {})


def test_cross_encoder_validates_as_reranker_and_resolves_rerank_target() -> None:
    # A cross-encoder serves the ``cross-encoder`` capability and resolves to a
    # remote HTTP rerank endpoint (the model runs out-of-container over HTTP,
    # e.g. a vLLM /v1/rerank server).
    target = resolve_rerank_target(
        "cross_encoder",
        {
            "url": "http://reranker.test",
            "port": 8000,
            "model_name": "BAAI/bge-reranker-v2-m3",
        },
    )
    assert target.provider == "http_rerank"
    assert target.model == "BAAI/bge-reranker-v2-m3"
    assert target.base_url == "http://reranker.test:8000"


def test_cross_encoder_validates_capability_and_fills_field_defaults() -> None:
    config = validate_provider("cross_encoder", "cross-encoder", {})
    assert config["model_name"] == "BAAI/bge-reranker-v2-m3"
    # Remote connection fields, like the other networked adapters.
    assert "url" in config
    assert "port" in config


def test_cross_encoder_cannot_be_used_as_embed_target() -> None:
    with pytest.raises(NotImplementedError, match="not an embedder"):
        resolve_embed_target("cross_encoder", {})


def test_cross_encoder_rejects_embedding_capability() -> None:
    with pytest.raises(ValueError, match="does not support"):
        validate_provider("cross_encoder", "embedding", {})


def test_openai_resolves_connection_settings() -> None:
    target = resolve_embed_target(
        "openai",
        {
            "url": "https://example.test/v1",
            "port": None,
            "api_key": "secret",
            "model_name": "embed-v1",
        },
    )
    assert target.provider == "openai"
    assert target.model == "embed-v1"
    assert target.base_url == "https://example.test/v1"
    assert target.api_key == "secret"
