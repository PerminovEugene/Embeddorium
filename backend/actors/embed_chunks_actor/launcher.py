"""Dramatiq launcher for the embed_chunks worker (pipeline stage 7)."""

import logging
import uuid
from typing import List, Optional

import dramatiq

from backend.actors.embed_chunks_actor.handler import (
    embed_chunks as _embed_chunks,
    get_embed_client_and_size,
)
from backend.shared import config
from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.clients.queue.queue_names import (
    EMBED_CHUNKS_ACTOR,
    EMBED_CHUNKS_QUEUE,
)
from backend.shared.log_routing import log_to
from backend.shared.logging_config import configure_logging
from backend.shared.models import PipelineActorConfigs
from backend.shared.storage.sql.core.engine import SqlPoolConfig
from backend.shared.storage.sql.sql_store import SqlStore
from backend.shared.storage.vector.collection_naming import (
    COLLECTION_SIMILARITY,
    UNSCOPED_DATASET_NAME,
    build_collection_name,
)
from backend.shared.storage.vector.vector_store import (
    VectorStore,
    similarity_to_distance,
)

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("embed_chunks")
dramatiq.set_broker(rabbitmq_broker)

# pool_size=2, max_overflow=3: dramatiq gives this worker its own concurrency
# via processes/threads, so the pool only needs to satisfy one process's
# threads, not the whole worker. See SqlPoolConfig for the full reasoning.
sql_store = SqlStore(
    pool_config=SqlPoolConfig(pool_size=2, max_overflow=3),
    application_name=EMBED_CHUNKS_ACTOR,
)


# Embed config keyed by pipeline_id. The PipelineRun snapshot is immutable
# after creation, so it is read from the DB once per pipeline and reused for
# every subsequent message of that pipeline instead of re-querying each time.
_embed_config: dict[str, tuple] = {}


def _load_embed_config(pipeline_id: Optional[str]):
    """Return ``(provider_type, model_type, provider_config, collection, distance)``.

    Reads the run's ``actor_configs.embed_chunks.provider`` snapshot and
    ``actor_configs.vector_store`` first, caching the result by ``pipeline_id``
    so the run row is loaded from the DB only the first time a given pipeline is
    seen. The snapshot's ``(provider_type, model_type, config)`` is returned
    as-is — the provider/model-type handler (via ``get_embed_client_and_size``)
    owns turning it into a client. Falls back to global env config if
    ``pipeline_id`` is absent,
    the run row is missing, or the snapshot can't be parsed — preserving the
    original single-provider behavior for legacy data. The fallback is not
    cached.
    """
    if pipeline_id is not None:
        cached = _embed_config.get(pipeline_id)
        if cached is not None:
            return cached

        try:
            run = sql_store.pipeline_runs.get(uuid.UUID(pipeline_id))
        except (ValueError, TypeError):
            run = None

        if run is not None:
            try:
                actor_cfg = PipelineActorConfigs.model_validate(run.actor_configs)
                # Provider snapshot lives in embed_chunks.provider, not
                # top-level. New snapshots nest type-specific settings under
                # "config"; older/flat snapshots keep them at the top level —
                # accept both, mirroring StandardEmbed.resolve().
                provider_snap = actor_cfg.embed_chunks.provider or {}
                provider_type = provider_snap.get("provider_type", "")
                model_type = provider_snap.get("model_type") or "embedding"
                provider_config = provider_snap.get("config") or provider_snap

                collection = actor_cfg.vector_store.collection
                distance = similarity_to_distance(actor_cfg.vector_store.similarity)

                result = (
                    provider_type,
                    model_type,
                    provider_config,
                    collection,
                    distance,
                )
                _embed_config[pipeline_id] = result
                return result
            except Exception:
                logger.warning(
                    "embed_chunks: could not parse run config for pipeline_id=%s",
                    pipeline_id,
                )

    # Fallback: global env / naming convention (legacy / no pipeline_id). There
    # is no dataset name to key the collection by here (that lived only in the
    # now-removed ``group`` field), so this degenerate path uses a fixed
    # placeholder collection — every current entry point records a
    # pipeline_id, so this should not be reachable in practice. The env provider
    # type resolves through the same adapter path as a snapshot; ``mock`` needs
    # its dimension supplied.
    collection = build_collection_name(UNSCOPED_DATASET_NAME)
    distance = similarity_to_distance(COLLECTION_SIMILARITY)
    provider_type = config.EMBED_PROVIDER
    model_type = "embedding"
    provider_config: dict = {}
    if provider_type == "mock":
        provider_config = {"mock_dim": config.MOCK_EMBED_DIM}
    return provider_type, model_type, provider_config, collection, distance


@dramatiq.actor(
    queue_name=EMBED_CHUNKS_QUEUE,
    actor_name=EMBED_CHUNKS_ACTOR,
    max_retries=3,
)
def embed_chunks(
    *,
    document_id: str,
    chunk_ids: List[str],
    pipeline_id: Optional[str] = None,
) -> None:
    # Collection, embedding provider/model and similarity all come from this
    # run's recorded pipeline_run config, not global config, so the query side
    # (DB search) and the index side agree on exactly one configuration.
    provider_type, model_type, provider_config, collection, distance = (
        _load_embed_config(pipeline_id)
    )

    model, model_size = get_embed_client_and_size(
        provider_type, model_type, provider_config
    )

    target = sql_store.crawl_targets.get_by_document_id(uuid.UUID(document_id))
    log_dir = target.log_dir if target is not None else None

    with log_to(log_dir, pipeline_id=pipeline_id):
        _embed_chunks(
            document_id=document_id,
            chunk_ids=chunk_ids,
            store=sql_store,
            vector_store=VectorStore(collection),
            model=model,
            model_size=model_size,
            distance=distance,
            pipeline_id=pipeline_id,
        )
