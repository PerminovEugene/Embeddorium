"""Dramatiq launcher for the chunk_document worker (pipeline stage 3)."""

import json
import logging
import uuid
from typing import Dict, Optional, Tuple

import dramatiq

from backend.actors.chunk_document_actor.handler import (
    chunk_document as _chunk_document,
)
from backend.plugins.chunkers.base import Chunker
from backend.plugins.chunkers.registry import DEFAULT_CHUNKER, build_chunker
from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.clients.queue.queue_names import (
    CHUNK_DOCUMENT_ACTOR,
    CHUNK_DOCUMENT_QUEUE,
)
from backend.shared.log_routing import log_to
from backend.shared.logging_config import configure_logging
from backend.shared.models import PipelineActorConfigs
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

# Built Chunker instances keyed by (chunker_name, settings-as-canonical-json)
# so each distinct run config builds its chunker once and reuses it across
# messages, mirroring the previous per-config TextSplitter cache.
_chunkers: Dict[Tuple[str, str], Chunker] = {}

# (chunker_name, settings) keyed by pipeline_id. The PipelineRun snapshot is
# immutable after creation, so it is read from the DB once per pipeline and
# reused for every subsequent message of that pipeline instead of
# re-querying each time.
_chunk_settings: Dict[str, Tuple[str, dict]] = {}


def _chunker_for(name: str, settings: dict) -> Chunker:
    # json.dumps with sort_keys gives a stable cache key regardless of dict
    # insertion order; default=str tolerates any non-JSON-native value a
    # chunker's settings might carry rather than raising here.
    key = (name, json.dumps(settings, sort_keys=True, default=str))
    if key not in _chunkers:
        _chunkers[key] = build_chunker(name, settings)
    return _chunkers[key]


def _load_chunk_settings(pipeline_id: Optional[str]) -> Tuple[str, dict]:
    """Return (chunker_name, settings) from the run's recorded actor_configs.

    Cached by ``pipeline_id`` so the run row is loaded from the DB only the
    first time a given pipeline is seen. Falls back to ``DEFAULT_CHUNKER``
    with empty settings when ``pipeline_id`` is absent or the run row is
    missing (legacy data or a pipeline started before this feature); the
    fallback is not cached.
    """
    if pipeline_id is None:
        return DEFAULT_CHUNKER, {}

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
            settings = (cfg.chunk_document.chunker, cfg.chunk_document.settings)
            _chunk_settings[pipeline_id] = settings
            return settings
        except Exception:
            logger.warning(
                "chunk_document: could not parse actor_configs for pipeline_id=%s",
                pipeline_id,
            )
    return DEFAULT_CHUNKER, {}


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

    # Chunker + its settings come from this run's recorded pipeline_run
    # actor_configs, not global config, so the run is honored even if env
    # config changes later.
    chunker_name, chunker_settings = _load_chunk_settings(pipeline_id)
    chunker = _chunker_for(chunker_name, chunker_settings)

    with log_to(log_dir, pipeline_id=pipeline_id):
        _chunk_document(
            crawl_target_id=crawl_target_id,
            group=group,
            pipeline_id=pipeline_id,
            store=sql_store,
            chunker=chunker,
        )
