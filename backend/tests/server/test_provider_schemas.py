"""camelCase API schema <-> generic provider domain mapping."""

from __future__ import annotations

import uuid

import pytest

from backend.server.providers.schemas import (
    ProviderIn,
    provider_in_to_domain,
    provider_to_out,
)
from backend.shared.models import Provider


def test_provider_input_resolves_adapter_defaults() -> None:
    payload = ProviderIn(
        name="oa",
        providerType="openai",
        modelType="embedding",
        config={"model_name": "text-embedding-3-small"},
    )

    domain = provider_in_to_domain(payload)

    assert domain.provider_type == "openai"
    # Missing keys are backfilled from the adapter's field defaults.
    assert domain.config["model_name"] == "text-embedding-3-small"
    assert "url" in domain.config


def test_provider_input_rejects_unsupported_capability() -> None:
    # mock only serves embedding, so requesting a text model must be rejected.
    payload = ProviderIn(
        name="m",
        providerType="mock",
        modelType="text",
        config={},
    )

    with pytest.raises(ValueError, match="does not support"):
        provider_in_to_domain(payload)


def test_provider_input_accepts_cross_encoder_under_ollama() -> None:
    # cross-encoder is a model type offered under the ollama provider now.
    payload = ProviderIn(
        name="reranker",
        providerType="ollama",
        modelType="cross-encoder",
        config={"model_name": "BAAI/bge-reranker-v2-m3"},
    )

    domain = provider_in_to_domain(payload)

    assert domain.provider_type == "ollama"
    assert domain.model_type == "cross-encoder"
    assert domain.config["model_name"] == "BAAI/bge-reranker-v2-m3"
    assert domain.config["rerank_path"] == "v1/rerank"
    assert "url" in domain.config


def test_provider_output_keeps_config_keys_snake_case() -> None:
    provider = Provider(
        id=uuid.uuid4(),
        name="ollama",
        provider_type="ollama",
        model_type="embedding",
        config={"model_name": "nomic-embed-text", "url": "http://localhost"},
    )

    dumped = provider_to_out(provider).model_dump(by_alias=True)

    assert dumped["providerType"] == "ollama"
    assert dumped["modelType"] == "embedding"
    assert dumped["config"]["model_name"] == "nomic-embed-text"


def test_unknown_provider_type_is_rejected() -> None:
    payload = ProviderIn(
        name="unknown",
        providerType="does-not-exist",
        modelType="embedding",
    )

    with pytest.raises(ValueError, match="Unknown provider type"):
        provider_in_to_domain(payload)
