"""Stage 7 (terminal): embed a batch of chunks and upsert vectors into Qdrant.

Pure logic — no broker/dramatiq concerns. The embedding model is loaded lazily
on first use and cached as a module singleton. The ``mock`` and ``ollama``
providers return/fetch vectors without importing torch/sentence-transformers,
so this module stays import-light in containers that run those providers —
only the ``huggingface`` (real local model) path pulls the heavy ML stack.

Once a batch's vectors are upserted, in one transaction this: (1) flips those
chunks' ``status`` to ``embedded``, (2) atomically finalizes the owning crawl
target to ``PROCESSED`` if — and only if — every chunk of its document is now
embedded (``UnitOfWork.finalize_target_if_all_chunks_embedded``; a no-op while
other chunks are still pending), and (3), when the batch belongs to a tracked
run, writes a tracker outbox event and bumps the run's ``embeddings_completed``
counter. This is what makes a target's ``PROCESSED`` status actually mean "its
chunks are embedded" instead of merely "its embed batches were scheduled" —
see ``schedule_discovered_links_actor`` for the target's status leading up to
this point, and ``track_pipeline_status_actor`` for the run-completion
condition that both this actor and ``schedule_discovered_links`` feed into.
"""

from __future__ import annotations

import uuid

from backend.shared import config
from backend.shared.clients.mock_embed_client import MockEmbedClient
from backend.shared.clients.queue.embed_chunks_payload import EmbedChunksPayload
from backend.shared.clients.queue.pipeline_payloads import TrackPipelineStatusPayload
from backend.shared.clients.queue.queue_names import (
    TRACK_PIPELINE_STATUS_ACTOR,
    TRACK_PIPELINE_STATUS_QUEUE,
)
from backend.shared.models import OutboxEvent
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
    store: SqlStore,
    vector_store: VectorStore,
    model,
    model_size: int,
    provider: str | None = None,
    distance=None,
    pipeline_id: str | None = None,
) -> None:
    payload = EmbedChunksPayload.from_actor_kwargs(
        document_id=document_id,
        chunk_ids=chunk_ids,
        pipeline_id=pipeline_id,
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
                    # Chunk classification (legal_body/act_title/...) so retrieval
                    # can prefer legal_body and gate amendment_history behind
                    # history/date queries.
                    "chunk_type": chunk.chunk_type,
                    # Lets DB search filter hits to a single pipeline run when
                    # several runs share one collection.
                    "pipeline_run_id": payload.pipeline_id,
                }
                for chunk in batch
            ],
        )

    # This whole invocation is one "batch" as far as schedule_embeddings and
    # track_pipeline_status are concerned (the BATCH_SIZE re-splitting above is
    # purely an internal encode-call chunking detail). Everything below runs
    # once, after every sub-batch has been upserted, so a partial failure never
    # marks a chunk embedded (or reports a batch as complete) prematurely.
    #
    # Marking chunks embedded and finalizing the target are unconditional
    # (independent of pipeline_id): the target's own status machine must stay
    # correct even for direct/untracked embed calls. Only the tracker event
    # and its counter are gated behind pipeline_id, since those exist purely
    # to drive a specific run's completion detection.
    if payload.chunk_ids:
        with store.unit_of_work() as uow:
            uow.mark_chunks_embedded(payload.chunk_ids)
            uow.finalize_target_if_all_chunks_embedded(payload.document_id)

            if payload.pipeline_id is not None:
                # The dedup key is keyed off the first chunk id of the whole
                # message, which is stable and unique per scheduled batch.
                track_payload = TrackPipelineStatusPayload(
                    pipeline_id=uuid.UUID(payload.pipeline_id)
                )
                inserted = uow.add_outbox(
                    OutboxEvent(
                        queue_name=TRACK_PIPELINE_STATUS_QUEUE,
                        actor_name=TRACK_PIPELINE_STATUS_ACTOR,
                        payload=track_payload.to_actor_kwargs(),
                        dedup_key=(
                            f"track:{payload.pipeline_id}:embed:"
                            f"{payload.document_id}:{payload.chunk_ids[0]}"
                        ),
                    )
                )
                if inserted:
                    uow.increment_embeddings_completed(
                        uuid.UUID(payload.pipeline_id), 1
                    )
