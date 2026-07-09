"""Dramatiq actor launcher for the Source Validator worker.

Sets up logging, the RabbitMQ broker, and the SQL store, then exposes the
``validate_source`` actor: it consumes validation messages from both chains
(web seed/discovered-link URLs and local file paths), applies the
per-source-type validation strategy, persists a ``CrawlTarget`` and enqueues
a fetch-source message for the new target.
"""

import logging
from typing import Optional

import dramatiq

from backend.actors.validate_source_actor.handler import handle
from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.clients.queue.queue_names import (
    VALIDATE_SOURCE_ACTOR,
    VALIDATE_SOURCE_QUEUE,
)
from backend.shared.logging_config import configure_logging
from backend.shared.storage.sql.core.engine import SqlPoolConfig
from backend.shared.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("validate_source")
dramatiq.set_broker(rabbitmq_broker)

# pool_size=2, max_overflow=3: dramatiq gives this worker its own concurrency
# via processes/threads, so the pool only needs to satisfy one process's
# threads, not the whole worker. See SqlPoolConfig for the full reasoning.
sql_store = SqlStore(
    pool_config=SqlPoolConfig(pool_size=2, max_overflow=3),
    application_name=VALIDATE_SOURCE_ACTOR,
)


@dramatiq.actor(
    queue_name=VALIDATE_SOURCE_QUEUE,
    actor_name=VALIDATE_SOURCE_ACTOR,
    max_retries=3,
)
def validate_source(
    *,
    url: str,
    parent_document_id: Optional[str] = None,
    parent_chunk_id: Optional[str] = None,
    pipeline_id: Optional[str] = None,
) -> None:
    logger.info("received source url=%s pipeline_id=%s", url, pipeline_id)

    handle(
        url=url,
        parent_document_id=parent_document_id,
        parent_chunk_id=parent_chunk_id,
        pipeline_id=pipeline_id,
        store=sql_store,
        broker=rabbitmq_broker,
    )
