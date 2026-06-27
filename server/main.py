from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from models import CompareRequest
from embedder import get_embeddings
from vector_store_utils import get_store, store_vectors
from matcher import match_embeddings
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
        source_embeddings = await get_embeddings(model_name, ollama_port, [t.text for t in source_texts])
        candidate_embeddings = await get_embeddings(model_name, ollama_port, [t.text for t in candidate_texts])

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


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
