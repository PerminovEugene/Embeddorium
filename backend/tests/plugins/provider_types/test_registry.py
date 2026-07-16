"""Provider/model-type discovery, defaults, and target resolution."""

from __future__ import annotations

import pytest

from backend.plugins.provider_types.registry import (
    build_embed_client,
    list_provider_type_configs,
    resolve_embed_target,
    resolve_rerank_target,
    validate_provider,
)
from backend.shared.clients.mock_embed_client import MockEmbedClient


def test_registry_discovers_builtin_providers() -> None:
    configs = {config.name: config for config in list_provider_type_configs()}
    # Only these three provider types exist — the reranker is no longer one.
    assert set(configs) == {"mock", "ollama", "openai"}
    assert "cross_encoder" not in configs
    assert "fastembed" not in configs
    assert configs["mock"].type == "builtin"
    assert configs["openai"].type == "remote"
    assert configs["ollama"].type == "remote"


def test_cross_encoder_is_a_model_type_under_ollama() -> None:
    configs = {config.name: config for config in list_provider_type_configs()}
    ollama = configs["ollama"]
    # cross-encoder is now a capability the ollama provider serves, not its own
    # provider type.
    assert "cross-encoder" in ollama.supported_model_types
    assert "embedding" in ollama.supported_model_types
    reranker = next(mt for mt in ollama.model_types if mt.model_type == "cross-encoder")
    field_keys = {f.key for f in reranker.fields}
    assert {"model_name", "rerank_path"} <= field_keys
    # Connection (url/port) lives on the provider, not the model type.
    conn_keys = {f.key for f in ollama.fields}
    assert {"url", "port"} <= conn_keys


def test_validate_provider_resolves_defaults_and_drops_unknown_keys() -> None:
    config = validate_provider(
        "ollama",
        "embedding",
        {"model_name": "nomic-embed-text", "unknown": "ignored"},
    )
    assert config["model_name"] == "nomic-embed-text"
    # Connection defaults are backfilled alongside the model-type fields.
    assert "url" in config
    assert "port" in config
    assert "unknown" not in config


def test_validate_provider_rejects_wrong_model_type() -> None:
    with pytest.raises(ValueError, match="does not support"):
        validate_provider("mock", "text", {})


def test_cross_encoder_resolves_rerank_target_over_http() -> None:
    # A cross-encoder serves the ``cross-encoder`` capability under ollama and
    # resolves to a remote HTTP rerank endpoint (the model runs out-of-container
    # over HTTP, e.g. a vLLM /v1/rerank server the provider's url/port points at).
    target = resolve_rerank_target(
        "ollama",
        "cross-encoder",
        {
            "url": "http://reranker.test",
            "port": 8000,
            "model_name": "BAAI/bge-reranker-v2-m3",
        },
    )
    assert target.provider == "http_rerank"
    assert target.model == "BAAI/bge-reranker-v2-m3"
    assert target.base_url == "http://reranker.test:8000"


def test_cross_encoder_fills_field_defaults() -> None:
    config = validate_provider("ollama", "cross-encoder", {})
    assert config["model_name"] == "BAAI/bge-reranker-v2-m3"
    assert config["rerank_path"] == "v1/rerank"
    # Remote connection fields come from the ollama provider.
    assert "url" in config
    assert "port" in config


def test_cross_encoder_cannot_be_used_as_embed_target() -> None:
    with pytest.raises(NotImplementedError, match="does not support embedding"):
        resolve_embed_target("ollama", "cross-encoder", {})


def test_build_embed_client_builds_the_handler_owned_client() -> None:
    # The mock embedding handler owns building its client from its own config —
    # the registry dispatches to it with no per-provider branching.
    client = build_embed_client("mock", "embedding", {"mock_dim": 12})
    assert isinstance(client, MockEmbedClient)
    assert client.get_embedding_dimension() == 12


def test_build_embed_client_rejects_unknown_type() -> None:
    # An unknown/legacy provider type must raise: the in-process HuggingFace
    # fallback was removed, so there is no local model to degrade to.
    with pytest.raises(ValueError, match="Unknown provider type"):
        build_embed_client("legacy_type", "embedding", {"model_name": "x"})


def test_resolve_embed_target_rejects_unknown_type() -> None:
    with pytest.raises(ValueError, match="Unknown provider type"):
        resolve_embed_target("legacy_type", "embedding", {"model_name": "x"})


def test_build_embed_client_rejects_a_reranker_capability() -> None:
    with pytest.raises(NotImplementedError, match="does not support embedding"):
        build_embed_client("ollama", "cross-encoder", {})


def test_openai_resolves_connection_settings() -> None:
    target = resolve_embed_target(
        "openai",
        "embedding",
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
