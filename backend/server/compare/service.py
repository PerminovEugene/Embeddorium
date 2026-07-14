"""Service layer for the ``/compare`` endpoint.

Embeds the user's source and candidate texts with the selected provider and
scores every source/candidate pair with the requested similarity metrics. The
route handler is a thin controller over ``compare_embeddings``.
"""

from __future__ import annotations

import logging
import uuid
from uuid import uuid4

from fastapi import HTTPException

from backend.plugins.provider_types.registry import resolve_embed_target
from backend.server.compare.embedder import get_embeddings
from backend.server.compare.matcher import match_embeddings
from backend.shared.storage.sql.sql_store import SqlStore


def _resolve_compare_provider(
    store: SqlStore,
    provider_id: str | None,
) -> tuple[str, str | None, str | None, int | None, str | None]:
    """Load the provider selected in the UI and return the args ``get_embeddings``
    needs: ``(provider_type, model_name, base_url, mock_dim, api_key)``.

    The embedding type/model/endpoint now come from a saved provider (picked by
    id in the compare form) instead of being sent inline by the client, so they
    can no longer be mismatched or spoofed from the browser. Connection
    settings are resolved by the selected provider adapter.
    """
    if not provider_id:
        raise HTTPException(status_code=400, detail="No provider selected")
    try:
        parsed = uuid.UUID(provider_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Provider not found")

    provider = store.providers.get(parsed)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    target = resolve_embed_target(provider.provider_type, provider.config)
    return (
        target.provider,
        target.model,
        target.base_url,
        target.mock_dim,
        target.api_key,
    )


async def compare_embeddings(store: SqlStore, request) -> dict:
    request_uuid = str(uuid4())

    provider_id = request.configuration.get("providerId")
    provider_type, model_name, base_url, mock_dim, api_key = _resolve_compare_provider(
        store, provider_id
    )

    logging.info("Comparing with provider=%s model=%s", provider_type, model_name)

    source_texts = request.source.inputs
    candidate_texts = request.candidates.inputs
    similarities = request.configuration.get("similarities")

    source_embeddings = await get_embeddings(
        provider_type,
        model_name,
        base_url,
        [t.text for t in source_texts],
        mock_dim=mock_dim,
        api_key=api_key,
    )
    candidate_embeddings = await get_embeddings(
        provider_type,
        model_name,
        base_url,
        [t.text for t in candidate_texts],
        mock_dim=mock_dim,
        api_key=api_key,
    )

    # Manual comparison computes similarities in-process from the embeddings
    # above; there's no need to round-trip vectors through Qdrant (and doing so
    # broke on model names containing ":", e.g. Ollama's "qwen3-embedding:latest",
    # which is an illegal Qdrant collection name). The model label just names the
    # embedding model; fall back to the provider type for the mock provider,
    # which serves no named model.
    store_key = model_name or provider_type

    matches = match_embeddings(
        source_embeddings,
        [t.id for t in source_texts],
        candidate_embeddings,
        [t.id for t in candidate_texts],
        similarities,
    )

    for match in matches:
        match["model"] = store_key

    return {
        "status": "success",
        "request_uuid": request_uuid,
        "matches": matches,
    }
