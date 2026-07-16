"""Stage 7 (terminal): embed a batch of chunks and upsert vectors into Qdrant.

Pure logic — no broker/dramatiq concerns. The embed *client* is provider-agnostic
here: this module never branches on the provider. It asks the selected
provider-type adapter to build its client (see
:func:`~backend.plugins.provider_types.registry.build_embed_client`) and then
drives that client through one uniform ``encode`` call. Each adapter imports its
own backend lazily, so this module stays import-light in containers that run the
network providers (ollama/openai) — every provider is reached over HTTP or is
the trivial mock, so no in-process model stack is ever pulled in.

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

import json
import uuid

from backend.plugins.provider_types.registry import build_embed_client
from backend.shared.clients.embed_client import EmbedClient
from backend.shared.clients.queue.embed_chunks_payload import EmbedChunksPayload
from backend.shared.clients.queue.pipeline_payloads import TrackPipelineStatusPayload
from backend.shared.clients.queue.queue_names import (
    TRACK_PIPELINE_STATUS_ACTOR,
    TRACK_PIPELINE_STATUS_QUEUE,
)
from backend.shared.models import OutboxEvent
from backend.shared.storage.sql.sql_store import SqlStore
from backend.shared.storage.vector.vector_store import VectorStore

BATCH_SIZE = 4

# Built embed clients, keyed by the resolved (provider_type, config) a run
# recorded — a single worker can serve several runs/providers, so the cache is
# keyed rather than a lone singleton. Populated lazily on first use, never at
# import time; each client's dimension is probed once and cached alongside it.
_clients: dict[str, tuple[EmbedClient, int]] = {}


def _cache_key(provider_type: str, model_type: str, values: dict | None) -> str:
    """A stable, hashable cache key for a ``(provider_type, model_type, config)``."""
    return json.dumps(
        [provider_type, model_type, values or {}], sort_keys=True, default=str
    )


def get_embed_client_and_size(
    provider_type: str,
    model_type: str,
    values: dict | None = None,
) -> tuple[EmbedClient, int]:
    """Return ``(client, dimension)`` for a run's recorded provider snapshot.

    Provider-agnostic: the selected provider/model-type handler owns how its
    client is built (:func:`build_embed_client`), so there is no per-provider
    branching here. The client and its probed dimension are cached the first time
    a given ``(provider_type, model_type, config)`` is seen.
    """
    key = _cache_key(provider_type, model_type, values)
    if key not in _clients:
        client = build_embed_client(provider_type, model_type, values)
        _clients[key] = (client, client.get_embedding_dimension())
    return _clients[key]


def embed_chunks(
    *,
    document_id: str,
    chunk_ids: list[str],
    store: SqlStore,
    vector_store: VectorStore,
    model: EmbedClient,
    model_size: int,
    distance=None,
    pipeline_id: str | None = None,
) -> None:
    payload = EmbedChunksPayload.from_actor_kwargs(
        document_id=document_id,
        chunk_ids=chunk_ids,
        pipeline_id=pipeline_id,
    )

    if distance is None:
        vector_store.create_collection(model_size)
    else:
        vector_store.create_collection(model_size, distance)

    chunks = store.chunks.get_many(payload.chunk_ids)

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]

        # Uniform for every provider: the client owns any backend-specific
        # concern (e.g. HTTP batching in the ollama/openai clients), so this
        # stays a plain encode call.
        embeddings = model.encode(
            [chunk.text for chunk in batch],
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

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
                    # Namespaced custom metadata; known system fields remain at
                    # top level for compatibility and efficient filtering.
                    "metadata": {
                        "system": {
                            "chunk_id": str(chunk.id),
                            "document_id": str(payload.document_id),
                            "pipeline_run_id": payload.pipeline_id,
                        },
                        "custom": dict(chunk.chunk_metadata),
                    },
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
