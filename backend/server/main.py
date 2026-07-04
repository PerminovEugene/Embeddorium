import uuid
from typing import Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from backend.server.models import CompareRequest, SearchRequest
from backend.server.embedder import get_embeddings
from backend.server.matcher import match_embeddings
from backend.server.db_search import search_db
from backend.shared import config
from backend.shared.storage.sql.sql_store import SqlStore
from backend.server.datasets_routes import router as datasets_router
from backend.server.providers_routes import router as providers_router
from backend.server.pipeline_routes import router as pipeline_router
from backend.server.source_files_routes import router as source_files_router
from backend.server.chunkers_routes import router as chunkers_router
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Embeddings Matcher API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets_router)
app.include_router(providers_router)
app.include_router(pipeline_router)
app.include_router(source_files_router)
app.include_router(chunkers_router)

@app.post("/compare")
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
        # No network: random vectors of a fixed dimension, mirroring db_search.
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


@app.post("/search")
async def search(request: SearchRequest):
    """Embed each source text and return its nearest vectors from the selected
    pipeline run's collection, enriched with chunk/document info from Postgres."""
    return await search_db(request)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
