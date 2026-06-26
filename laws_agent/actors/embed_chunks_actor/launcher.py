"""Dramatiq launcher for the embed_chunks worker (pipeline stage 7)."""

import logging
import uuid

import dramatiq

from laws_agent.actors.embed_chunks_actor.handler import (
    embed_chunks as _embed_chunks,
    get_model_and_size,
)
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.queue_names import (
    EMBED_CHUNKS_ACTOR,
    EMBED_CHUNKS_QUEUE,
)
from laws_agent.log_routing import log_to
from laws_agent.logging_config import configure_logging
from laws_agent.storage.sql.core.engine import SqlPoolConfig
from laws_agent.storage.sql.sql_store import SqlStore
from laws_agent.storage.vector.vector_store import VectorStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("embed_chunks")
dramatiq.set_broker(rabbitmq_broker)

COLLECTION_BASE = "LAWS"
MODEL_COLLECTION_POSTFIX = "qwen_embed_8b"

# pool_size=2, max_overflow=3: dramatiq gives this worker its own concurrency
# via processes/threads, so the pool only needs to satisfy one process's
# threads, not the whole worker. See SqlPoolConfig for the full reasoning.
sql_store = SqlStore(
    pool_config=SqlPoolConfig(pool_size=2, max_overflow=3),
    application_name=EMBED_CHUNKS_ACTOR,
)


@dramatiq.actor(
    queue_name=EMBED_CHUNKS_QUEUE,
    actor_name=EMBED_CHUNKS_ACTOR,
    max_retries=3,
)
def embed_chunks(*, document_id: str, chunk_ids: list[str], group: str) -> None:
    collection = f"{COLLECTION_BASE}_{group}_{MODEL_COLLECTION_POSTFIX}"
    model, model_size = get_model_and_size()

    target = sql_store.crawl_targets.get_by_document_id(uuid.UUID(document_id))
    log_dir = target.log_dir if target is not None else None

    with log_to(log_dir):
        _embed_chunks(
            document_id=document_id,
            chunk_ids=chunk_ids,
            group=group,
            store=sql_store,
            vector_store=VectorStore(collection),
            model=model,
            model_size=model_size,
        )
