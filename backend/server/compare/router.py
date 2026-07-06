"""Route handler for the ``/compare`` endpoint.

Embeds the user's source and candidate texts with the selected provider and
scores every source/candidate pair with the requested similarity metrics.
"""

import logging
import uuid
from typing import Optional, Tuple
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from backend.server.compare.embedder import get_embeddings
from backend.server.compare.matcher import match_embeddings
from backend.server.compare.schemas import CompareRequest
from backend.shared import config
from backend.shared.storage.sql.sql_store import SqlStore

router = APIRouter(tags=["compare"])


@router.post("/compare")
async def compare(request: CompareRequest):
    return await compare_embeddings(request)


def _resolve_compare_provider(
    provider_id: Optional[str],
) -> Tuple[str, Optional[str], Optional[str], Optional[int]]:
    """Load the provider selected in the UI and return the args ``get_embeddings``
    needs: ``(provider_type, model_name, ollama_port, mock_dim)``.

    The embedding type/model/port now come from a saved provider (picked by id
    in the compare form) instead of being sent inline by the client, so they can
    no longer be mismatched or spoofed from the browser.
    """
    if not provider_id:
        raise HTTPException(status_code=400, detail="No provider selected")
    try:
        parsed = uuid.UUID(provider_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Provider not found")

    store = SqlStore(application_name="embeddorium-compare")
    try:
        provider = store.providers.get(parsed)
    finally:
        store.close()
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")

    if provider.provider_type == "mock":
        # No network: random vectors of a fixed dimension, mirroring search.service.
        return "mock", None, None, config.MOCK_EMBED_DIM
    if provider.provider_type == "ollama":
        return "ollama", provider.model_name, str(provider.port), None
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported provider type for compare: {provider.provider_type}",
    )


async def compare_embeddings(request):
    request_uuid = str(uuid4())

    provider_id = request.configuration.get("providerId")
    provider_type, model_name, ollama_port, mock_dim = _resolve_compare_provider(
        provider_id
    )

    logging.info("Comparing with provider=%s model=%s", provider_type, model_name)

    source_texts = request.source.inputs
    candidate_texts = request.candidates.inputs
    similarities = request.configuration.get("similarities")

    source_embeddings = await get_embeddings(
        provider_type, model_name, ollama_port, [t.text for t in source_texts], mock_dim=mock_dim
    )
    candidate_embeddings = await get_embeddings(
        provider_type, model_name, ollama_port, [t.text for t in candidate_texts], mock_dim=mock_dim
    )

    # Manual comparison computes similarities in-process from the embeddings
    # above; there's no need to round-trip vectors through Qdrant (and doing so
    # broke on model names containing ":", e.g. Ollama's "qwen3-embedding:latest",
    # which is an illegal Qdrant collection name). The model label just names the
    # embedding model; fall back to the provider type for the mock provider,
    # which serves no named model.
    store_key = model_name or provider_type

    matches = match_embeddings(
        source_embeddings, [t.id for t in source_texts],
        candidate_embeddings, [t.id for t in candidate_texts],
        similarities
    )

    for match in matches:
        match["model"] = store_key

    return {
        "status": "success",
        "request_uuid": request_uuid,
        "matches": matches
    }
