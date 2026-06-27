"""Stage 7: embed a batch of chunks and upsert vectors into Qdrant.

Pure logic — no broker/dramatiq concerns. The embedding model is loaded lazily
on first use and cached as a module singleton. The ``mock`` and ``ollama``
providers return/fetch vectors without importing torch/sentence-transformers,
so this module stays import-light in containers that run those providers —
only the ``huggingface`` (real local model) path pulls the heavy ML stack.
"""

from __future__ import annotations

from laws_agent import config
from laws_agent.clients.mock_embed_client import MockEmbedClient
from laws_agent.clients.queue.embed_chunks_payload import EmbedChunksPayload
from laws_agent.storage.sql.sql_store import SqlStore
from laws_agent.storage.vector.vector_store import VectorStore

MODEL_NAME = "Qwen/Qwen3-Embedding-8B"
BATCH_SIZE = 4

# Providers that never need torch (no local model load).
_NO_TORCH_PROVIDERS = frozenset({"mock", "ollama"})

# Lazy singletons — initialized on first call, not at import time.
_model = None
_model_size: int | None = None


def get_model_and_size():
    global _model, _model_size
    if _model is None:
        if config.EMBED_PROVIDER == "mock":
            # No model load, no torch/sentence-transformers work — just random
            # vectors of the configured size, for fast pipeline dry runs.
            _model = MockEmbedClient(config.MOCK_EMBED_DIM)
            _model_size = config.MOCK_EMBED_DIM
        elif config.EMBED_PROVIDER == "ollama":
            # Deferred import: avoids pulling langchain_ollama/ollama when
            # EMBED_PROVIDER is something else.
            from laws_agent.clients.ollama_embed_client import OllamaEmbedClient

            _model = OllamaEmbedClient(
                model=config.OLLAMA_EMBED_MODEL,
                base_url=config.OLLAMA_EMBED_BASE_URL,
            )
            _model_size = _model.get_embedding_dimension()
        else:
            # Deferred import: avoids loading torch/sentence-transformers when
            # EMBED_PROVIDER is "mock" or "ollama".
            from laws_agent.clients.hg_client import HgClient

            hg_client = HgClient()
            _model = hg_client.get_model(MODEL_NAME)
            _model_size = hg_client.get_model_size(MODEL_NAME)
    return _model, _model_size


def embed_chunks(
    *,
    document_id: str,
    chunk_ids: list[str],
    group: str,
    store: SqlStore,
    vector_store: VectorStore,
    model,
    model_size: int,
) -> None:
    payload = EmbedChunksPayload.from_actor_kwargs(
        document_id=document_id,
        chunk_ids=chunk_ids,
        group=group,
    )

    vector_store.create_collection(model_size)

    chunks = store.chunks.get_many(payload.chunk_ids)

    skip_torch = config.EMBED_PROVIDER in _NO_TORCH_PROVIDERS

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
