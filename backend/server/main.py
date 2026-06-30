from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from backend.server.models import CompareRequest, SearchRequest
from backend.server.embedder import get_embeddings
from backend.server.vector_store_utils import get_store, store_vectors
from backend.server.matcher import match_embeddings
from backend.server.db_search import search_db
from backend.server.datasets_routes import router as datasets_router
from backend.server.providers_routes import router as providers_router
from backend.server.pipeline_routes import router as pipeline_router
from backend.server.source_files_routes import router as source_files_router
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

@app.post("/compare")
async def compare(request: CompareRequest):
    return await compare_embeddings(request)

async def compare_embeddings(request):
    request_uuid = str(uuid4())

    model_names = request.configuration.get("modelNames")
    ollama_port = request.configuration.get("ollamaPort")

    logging.info("Comparing with models: %s", model_names)

    source_texts = request.source.inputs
    candidate_texts = request.candidates.inputs
    similarities = request.configuration.get("similarities")

    all_results = []

    for model_name in model_names:
        source_embeddings = await get_embeddings("ollama", model_name, ollama_port, [t.text for t in source_texts])
        candidate_embeddings = await get_embeddings("ollama", model_name, ollama_port, [t.text for t in candidate_texts])

        dim_size = len(source_embeddings[0])
        store = get_store(model_name, dim_size)

        store_vectors(store, source_texts, source_embeddings, request_uuid, f"source_{model_name}")
        store_vectors(store, candidate_texts, candidate_embeddings, request_uuid, f"candidates_{model_name}")

        matches = match_embeddings(
            source_embeddings, [t.id for t in source_texts],
            candidate_embeddings, [t.id for t in candidate_texts],
            similarities
        )

        for match in matches:
            match["model"] = model_name
            all_results.append(match)

    return {
        "status": "success",
        "request_uuid": request_uuid,
        "matches": all_results
    }


@app.post("/search")
async def search(request: SearchRequest):
    """Embed each source text and return its nearest vectors from the selected
    pipeline run's collection, enriched with chunk/document info from Postgres."""
    return await search_db(request)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
