"""CRUD endpoints for ``Provider`` rows (``/providers``).

A provider supplies a model (Ollama, a remote OpenAI-compatible endpoint, or
a mock for testing). Request/response bodies use camelCase to match the UI's
``Provider`` union (``ui/src/components/providers/types.ts``); see
``providers/schemas.py`` for the camelCase<->domain mapping.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from backend.server.providers.schemas import (
    ProviderIn,
    ProviderOut,
    provider_in_to_domain,
    provider_to_out,
)
from backend.shared.storage.sql.sql_store import SqlStore

router = APIRouter(prefix="/providers", tags=["providers"])


def _parse_id(provider_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(provider_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Provider not found")


@router.get("", response_model=list[ProviderOut], response_model_by_alias=True)
async def list_providers() -> list[ProviderOut]:
    """List every provider, newest first."""
    store = SqlStore(application_name="embeddorium-providers")
    try:
        return [provider_to_out(p) for p in store.providers.list_recent()]
    finally:
        store.close()


@router.post("", response_model=ProviderOut, response_model_by_alias=True)
async def create_provider(payload: ProviderIn) -> ProviderOut:
    """Create a provider and return it with its generated id."""
    store = SqlStore(application_name="embeddorium-providers")
    try:
        created = store.providers.create(provider_in_to_domain(payload))
        return provider_to_out(created)
    finally:
        store.close()


@router.get(
    "/{provider_id}", response_model=ProviderOut, response_model_by_alias=True
)
async def get_provider(provider_id: str) -> ProviderOut:
    """Fetch a single provider by id, or 404 if it doesn't exist."""
    parsed = _parse_id(provider_id)
    store = SqlStore(application_name="embeddorium-providers")
    try:
        provider = store.providers.get(parsed)
        if provider is None:
            raise HTTPException(status_code=404, detail="Provider not found")
        return provider_to_out(provider)
    finally:
        store.close()


@router.put(
    "/{provider_id}", response_model=ProviderOut, response_model_by_alias=True
)
async def update_provider(provider_id: str, payload: ProviderIn) -> ProviderOut:
    """Replace a provider's fields, or 404 if it doesn't exist."""
    parsed = _parse_id(provider_id)
    store = SqlStore(application_name="embeddorium-providers")
    try:
        updated = store.providers.update(parsed, provider_in_to_domain(payload))
        if updated is None:
            raise HTTPException(status_code=404, detail="Provider not found")
        return provider_to_out(updated)
    finally:
        store.close()


@router.delete("/{provider_id}")
async def delete_provider(provider_id: str) -> dict:
    """Delete a provider, or 404 if it doesn't exist."""
    parsed = _parse_id(provider_id)
    store = SqlStore(application_name="embeddorium-providers")
    try:
        deleted = store.providers.delete(parsed)
        if not deleted:
            raise HTTPException(status_code=404, detail="Provider not found")
        return {"status": "deleted"}
    finally:
        store.close()
