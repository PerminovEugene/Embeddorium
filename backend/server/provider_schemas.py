"""camelCase API schemas for the ``/providers`` endpoints.

Mirrors the UI's discriminated ``Provider`` union (``ui/src/components/
providers/types.ts``) field-for-field, so request/response bodies need no
reshaping on the frontend. These are pure API-layer models: route handlers
translate to/from the snake_case domain models in ``backend.shared.models``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from backend.shared.models import (
    ModelType,
    MockProvider,
    OllamaProvider,
    Provider,
    RemoteProvider,
)


class _CamelModel(BaseModel):
    """Base for API schemas: camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class OllamaProviderIn(_CamelModel):
    """Request body for creating/updating an Ollama provider."""

    name: str
    model_type: ModelType
    provider_type: Literal["ollama"] = "ollama"
    port: int
    model_name: str


class RemoteProviderIn(_CamelModel):
    """Request body for creating/updating a remote (OpenAI-compatible) provider."""

    name: str
    model_type: ModelType
    provider_type: Literal["remote"] = "remote"
    base_url: str
    api_key: str
    organization: str
    model_name: str


class MockProviderIn(_CamelModel):
    """Request body for creating/updating a mock provider."""

    name: str
    model_type: ModelType
    provider_type: Literal["mock"] = "mock"


ProviderIn = Annotated[
    Union[OllamaProviderIn, RemoteProviderIn, MockProviderIn],
    Field(discriminator="provider_type"),
]


class OllamaProviderOut(_CamelModel):
    """Response body for an Ollama provider."""

    id: uuid.UUID
    name: str
    model_type: ModelType
    provider_type: Literal["ollama"] = "ollama"
    port: int
    model_name: str
    created_at: Optional[datetime] = None


class RemoteProviderOut(_CamelModel):
    """Response body for a remote (OpenAI-compatible) provider."""

    id: uuid.UUID
    name: str
    model_type: ModelType
    provider_type: Literal["remote"] = "remote"
    base_url: str
    api_key: str
    organization: str
    model_name: str
    created_at: Optional[datetime] = None


class MockProviderOut(_CamelModel):
    """Response body for a mock provider."""

    id: uuid.UUID
    name: str
    model_type: ModelType
    provider_type: Literal["mock"] = "mock"
    created_at: Optional[datetime] = None


ProviderOut = Union[OllamaProviderOut, RemoteProviderOut, MockProviderOut]


def provider_in_to_domain(payload: ProviderIn) -> Provider:
    """Map a validated camelCase request body to its snake_case domain model."""
    if payload.provider_type == "ollama":
        return OllamaProvider(
            name=payload.name,
            model_type=payload.model_type,
            port=payload.port,
            model_name=payload.model_name,
        )
    if payload.provider_type == "remote":
        return RemoteProvider(
            name=payload.name,
            model_type=payload.model_type,
            base_url=payload.base_url,
            api_key=payload.api_key,
            organization=payload.organization,
            model_name=payload.model_name,
        )
    return MockProvider(name=payload.name, model_type=payload.model_type)


def provider_to_out(provider: Provider) -> ProviderOut:
    """Map a snake_case domain model to its camelCase response schema."""
    if isinstance(provider, OllamaProvider):
        return OllamaProviderOut(
            id=provider.id,
            name=provider.name,
            model_type=provider.model_type,
            port=provider.port,
            model_name=provider.model_name,
            created_at=provider.created_at,
        )
    if isinstance(provider, RemoteProvider):
        return RemoteProviderOut(
            id=provider.id,
            name=provider.name,
            model_type=provider.model_type,
            base_url=provider.base_url,
            api_key=provider.api_key,
            organization=provider.organization,
            model_name=provider.model_name,
            created_at=provider.created_at,
        )
    return MockProviderOut(
        id=provider.id,
        name=provider.name,
        model_type=provider.model_type,
        created_at=provider.created_at,
    )
