"""Stage 7: embed a batch of chunks and upsert vectors into Qdrant.

Pure logic — no broker/dramatiq concerns. The embedding model is loaded lazily
on first use and cached as a module singleton. The ``mock`` and ``ollama``
providers return/fetch vectors without importing torch/sentence-transformers,
so this module stays import-light in containers that run those providers —
only the ``huggingface`` (real local model) path pulls the heavy ML stack.
"""

from __future__ import annotations

from backend.shared import config
from backend.shared.clients.mock_embed_client import MockEmbedClient
from backend.shared.clients.queue.embed_chunks_payload import EmbedChunksPayload
from backend.shared.storage.sql.sql_store import SqlStore
from backend.shared.storage.vector.vector_store import VectorStore

MODEL_NAME = "Qwen/Qwen3-Embedding-8B"
BATCH_SIZE = 4

# Providers that never need torch (no local model load).
_NO_TORCH_PROVIDERS = frozenset({"mock", "ollama"})

# Loaded embedding models, keyed by (provider, model) — a single worker can now
# serve several runs/providers, so the cache is keyed instead of a lone
# singleton. Populated lazily on first use, never at import time.
_models: dict[tuple[str, str], tuple] = {}


def get_model_and_size(
    provider: str | None = None,
    model: str | None = None,
    mock_dim: int | None = None,
):
    """Return ``(model, size)`` for *provider*/*model*, loading + caching once.

    Arguments come from a run's recorded embed config; each falls back to the
    global env default when omitted, preserving the original single-provider
    behavior for callers that don't pass them.
    """
    provider = provider or config.EMBED_PROVIDER
    if provider == "ollama":
        model = model or config.OLLAMA_EMBED_MODEL
    elif provider == "mock":
        model = model or "mock"
    else:
        model = model or MODEL_NAME

    key = (provider, model)
    if key not in _models:
        if provider == "mock":
            # No model load, no torch/sentence-transformers work — just random
            # vectors of the configured size, for fast pipeline dry runs.
            dim = mock_dim if mock_dim is not None else config.MOCK_EMBED_DIM
            _models[key] = (MockEmbedClient(dim), dim)
        elif provider == "ollama":
            # Deferred import: avoids pulling langchain_ollama/ollama when the
            # provider is something else.
            from backend.shared.clients.ollama_embed_client import OllamaEmbedClient

            client = OllamaEmbedClient(
                model=model,
                base_url=config.OLLAMA_EMBED_BASE_URL,
            )
            _models[key] = (client, client.get_embedding_dimension())
        else:
            # Deferred import: avoids loading torch/sentence-transformers when
            # the provider is "mock" or "ollama".
            from backend.shared.clients.hg_client import HgClient

            hg_client = HgClient()
            _models[key] = (hg_client.get_model(model), hg_client.get_model_size(model))
    return _models[key]


def embed_chunks(
    *,
    document_id: str,
    chunk_ids: list[str],
    group: str,
    store: SqlStore,
    vector_store: VectorStore,
    model,
    model_size: int,
    provider: str | None = None,
    distance=None,
) -> None:
    payload = EmbedChunksPayload.from_actor_kwargs(
        document_id=document_id,
        chunk_ids=chunk_ids,
        group=group,
    )

    # provider/distance come from the run's recorded config; both fall back so
    # direct callers (and tests) that omit them keep the original behavior.
    provider = provider or config.EMBED_PROVIDER

    if distance is None:
        vector_store.create_collection(model_size)
    else:
        vector_store.create_collection(model_size, distance)

    chunks = store.chunks.get_many(payload.chunk_ids)

    skip_torch = provider in _NO_TORCH_PROVIDERS

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]

        if skip_torch:
            # No local model, no GPU/MPS bookkeeping needed.
            embeddings = model.encode(
                [chunk.text for chunk in batch],
                batch_size=BATCH_SIZE,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
        else:
            import torch

            with torch.no_grad():
                embeddings = model.encode(
                    [chunk.text for chunk in batch],
                    batch_size=BATCH_SIZE,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )

            if torch.backends.mps.is_available():
                torch.mps.empty_cache()

        vector_store.upsert(
            ids=[str(chunk.id) for chunk in batch],
            vectors=[embedding.tolist() for embedding in embeddings],
            payloads=[
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(payload.document_id),
                    "chunk_index": chunk.chunk_index,
                    "group": payload.group,
                }
                for chunk in batch
            ],
        )
