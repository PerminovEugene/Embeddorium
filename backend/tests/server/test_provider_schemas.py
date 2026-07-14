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
        name="fe",
        providerType="fastembed",
        modelType="embedding",
        config={},
    )

    domain = provider_in_to_domain(payload)

    assert domain.provider_type == "fastembed"
    assert domain.config == {"model_name": "BAAI/bge-small-en-v1.5"}


def test_provider_input_rejects_unsupported_capability() -> None:
    payload = ProviderIn(
        name="fe",
        providerType="fastembed",
        modelType="text",
        config={},
    )

    with pytest.raises(ValueError, match="does not support"):
        provider_in_to_domain(payload)


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
