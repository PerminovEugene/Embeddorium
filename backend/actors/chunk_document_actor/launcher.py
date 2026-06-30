"""Dramatiq launcher for the chunk_document worker (pipeline stage 3)."""

import logging
import uuid
from typing import Optional

import dramatiq

from backend.actors.chunk_document_actor.handler import (
    chunk_document as _chunk_document,
)
from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.clients.queue.queue_names import (
    CHUNK_DOCUMENT_ACTOR,
    CHUNK_DOCUMENT_QUEUE,
)
from backend.shared.log_routing import log_to
from backend.shared.logging_config import configure_logging
from backend.shared.models import PipelineActorConfigs
from backend.shared.parsers.chunking_config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHUNK_STRATEGY,
)
from backend.shared.parsers.text_splitter import TextSplitter
from backend.shared.storage.sql.core.engine import SqlPoolConfig
from backend.shared.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("chunk_document")
dramatiq.set_broker(rabbitmq_broker)

# pool_size=2, max_overflow=3: dramatiq gives this worker its own concurrency
# via processes/threads, so the pool only needs to satisfy one process's
# threads, not the whole worker. See SqlPoolConfig for the full reasoning.
sql_store = SqlStore(
    pool_config=SqlPoolConfig(pool_size=2, max_overflow=3),
    application_name=CHUNK_DOCUMENT_ACTOR,
)

# Splitters keyed by (strategy, chunk_size, chunk_overlap) so each distinct
# run config builds its TextSplitter once and reuses it across messages.
_splitters: dict = {}

# Chunk settings keyed by pipeline_id. The PipelineRun snapshot is immutable
# after creation, so it is read from the DB once per pipeline and reused for
# every subsequent message of that pipeline instead of re-querying each time.
_chunk_settings: dict[str, tuple[str, int, int]] = {}


def _splitter_for(strategy: str, chunk_size: int, chunk_overlap: int) -> TextSplitter:
    key = (strategy, chunk_size, chunk_overlap)
    if key not in _splitters:
        _splitters[key] = TextSplitter(
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    return _splitters[key]


def _load_chunk_settings(pipeline_id: Optional[str]):
    """Return (strategy, chunk_size, chunk_overlap) from the run's actor_configs.

    Cached by ``pipeline_id`` so the run row is loaded from the DB only the
    first time a given pipeline is seen. Falls back to global constants when
    ``pipeline_id`` is absent or the run row is missing (legacy data or a
    pipeline started before this feature); the fallback is not cached.
    """
    if pipeline_id is None:
        return CHUNK_STRATEGY, CHUNK_SIZE, CHUNK_OVERLAP

    cached = _chunk_settings.get(pipeline_id)
    if cached is not None:
        return cached

    try:
        run = sql_store.pipeline_runs.get(uuid.UUID(pipeline_id))
    except (ValueError, TypeError):
        run = None
    if run is not None:
        try:
            cfg = PipelineActorConfigs.model_validate(run.actor_configs)
            settings = (
                cfg.chunk_document.strategy,
                cfg.chunk_document.chunk_size,
                cfg.chunk_document.chunk_overlap,
            )
            _chunk_settings[pipeline_id] = settings
            return settings
        except Exception:
            logger.warning(
                "chunk_document: could not parse actor_configs for pipeline_id=%s",
                pipeline_id,
            )
    return CHUNK_STRATEGY, CHUNK_SIZE, CHUNK_OVERLAP


@dramatiq.actor(
    queue_name=CHUNK_DOCUMENT_QUEUE,
    actor_name=CHUNK_DOCUMENT_ACTOR,
    max_retries=3,
)
def chunk_document(
    *, crawl_target_id: str, group: str, pipeline_id: Optional[str] = None
) -> None:
    target = sql_store.crawl_targets.get(uuid.UUID(crawl_target_id))
    log_dir = target.log_dir if target is not None else None

    # Chunk strategy/sizing come from this run's recorded pipeline_run
    # actor_configs, not global config, so the run is honored even if env
    # config changes later.
    strategy, chunk_size, chunk_overlap = _load_chunk_settings(pipeline_id)
    splitter = _splitter_for(strategy, chunk_size, chunk_overlap)

    with log_to(log_dir, pipeline_id=pipeline_id):
        _chunk_document(
            crawl_target_id=crawl_target_id,
            group=group,
            pipeline_id=pipeline_id,
            store=sql_store,
            splitter=splitter,
        )
