"""camelCase API schemas for the ``/providers`` endpoints.

A provider is a single flat record now — ``{providerType, name, modelType,
config}`` — instead of a discriminated union of one schema per type. ``config``
is the type-specific settings blob; its keys are the exact snake_case field
keys the provider-type adapter declares (``model_name``, ``url``, ``mock_dim``,
...) and are sent back verbatim, so the blob is *not* camelCased. On create/
update the blob is resolved against the selected adapter's field defaults, so a
partial config still persists a complete one.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from backend.plugins.provider_types.registry import validate_provider
from backend.shared.models import ModelType, Provider


class _CamelModel(BaseModel):
    """Base for API schemas: camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ProviderIn(_CamelModel):
    """Request body for creating/updating a provider."""

    name: str
    provider_type: str
    model_type: ModelType
    # Type-specific settings. Keys are the adapter's snake_case field keys and
    # are stored verbatim (never camelCased).
    config: dict[str, Any] = Field(default_factory=dict)


class ProviderOut(_CamelModel):
    """Response body for a provider."""

    id: uuid.UUID
    name: str
    provider_type: str
    model_type: ModelType
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


def provider_in_to_domain(payload: ProviderIn) -> Provider:
    """Map a validated request body to a domain ``Provider``.

    Resolves ``config`` against the selected provider-type adapter's field
    defaults. Raises ``ValueError`` for an unknown ``provider_type`` (the router
    turns that into a 400).
    """
    config = validate_provider(
        payload.provider_type,
        payload.model_type,
        payload.config,
    )
    return Provider(
        name=payload.name,
        provider_type=payload.provider_type,
        model_type=payload.model_type,
        config=config,
    )


def provider_to_out(provider: Provider) -> ProviderOut:
    """Map a domain ``Provider`` to its camelCase response schema."""
    return ProviderOut(
        id=provider.id,
        name=provider.name,
        provider_type=provider.provider_type,
        model_type=provider.model_type,
        config=dict(provider.config or {}),
        created_at=provider.created_at,
    )
