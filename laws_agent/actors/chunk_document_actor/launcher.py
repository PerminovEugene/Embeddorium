"""Dramatiq launcher for the chunk_document worker (pipeline stage 3)."""

import logging
import uuid

import dramatiq

from laws_agent.actors.chunk_document_actor.handler import (
    chunk_document as _chunk_document,
)
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.queue_names import (
    CHUNK_DOCUMENT_ACTOR,
    CHUNK_DOCUMENT_QUEUE,
)
from laws_agent.log_routing import log_to
from laws_agent.logging_config import configure_logging
from laws_agent.parsers.text_splitter import TextSplitter
from laws_agent.pipeline.run_config import load_pipeline_run
from laws_agent.storage.sql.core.engine import SqlPoolConfig
from laws_agent.storage.sql.sql_store import SqlStore

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

# Splitters keyed by (chunk_size, chunk_overlap) so each distinct run config
# builds its MarkdownTextSplitter once and reuses it across messages.
_splitters: dict[tuple[int, int], TextSplitter] = {}


def _splitter_for(chunk_size: int, chunk_overlap: int) -> TextSplitter:
    key = (chunk_size, chunk_overlap)
    if key not in _splitters:
        _splitters[key] = TextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
    return _splitters[key]


@dramatiq.actor(
    queue_name=CHUNK_DOCUMENT_QUEUE,
    actor_name=CHUNK_DOCUMENT_ACTOR,
    max_retries=3,
)
def chunk_document(*, crawl_target_id: str, group: str) -> None:
    target = sql_store.crawl_targets.get(uuid.UUID(crawl_target_id))
    log_dir = target.log_dir if target is not None else None

    # Chunk sizing comes from this group's recorded pipeline run, not global
    # config, so the run is honored even if env config changes later.
    chunk_cfg = load_pipeline_run(sql_store, group).settings.chunk_document
    splitter = _splitter_for(chunk_cfg.chunk_size, chunk_cfg.chunk_overlap)

    with log_to(log_dir):
        _chunk_document(
            crawl_target_id=crawl_target_id,
            group=group,
            store=sql_store,
            splitter=splitter,
        )
