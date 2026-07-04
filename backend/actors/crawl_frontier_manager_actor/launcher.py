"""Dramatiq actor launcher for the Crawl Frontier Manager worker.

Sets up logging, the RabbitMQ broker, and the SQL store, then exposes the
``manage_crawl_frontier`` actor: it consumes crawl-frontier messages, normalizes
the URL, skips already-queued or disallowed URLs, persists a ``CrawlTarget``,
and enqueues a fetch-source message for the new target.
"""

import logging
from typing import Optional

import dramatiq

from backend.actors.crawl_frontier_manager_actor.handler import handle
from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.clients.queue.queue_names import (
    CRAWL_FRONTIER_MANAGER_ACTOR,
    CRAWL_FRONTIER_MANAGER_QUEUE,
)
from backend.shared.logging_config import configure_logging
from backend.shared.storage.sql.core.engine import SqlPoolConfig
from backend.shared.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

logger.info("setup broker")
rabbitmq_broker = QueueClient().create("crawl_frontier_manager")
dramatiq.set_broker(rabbitmq_broker)
logger.info("setup broker done broker=%s", rabbitmq_broker)

# pool_size=2, max_overflow=3: dramatiq gives this worker its own concurrency
# via processes/threads, so the pool only needs to satisfy one process's
# threads, not the whole worker. See SqlPoolConfig for the full reasoning.
sql_store = SqlStore(
    pool_config=SqlPoolConfig(pool_size=2, max_overflow=3),
    application_name=CRAWL_FRONTIER_MANAGER_ACTOR,
)


@dramatiq.actor(
    queue_name=CRAWL_FRONTIER_MANAGER_QUEUE,
    actor_name=CRAWL_FRONTIER_MANAGER_ACTOR,
    max_retries=3,
)
def manage_crawl_frontier(
    *,
    url: str,
    parent_document_id: Optional[str] = None,
    parent_chunk_id: Optional[str] = None,
    pipeline_id: Optional[str] = None,
) -> None:
    logger.info("received link url=%s pipeline_id=%s", url, pipeline_id)

    handle(
        url=url,
        parent_document_id=parent_document_id,
        parent_chunk_id=parent_chunk_id,
        pipeline_id=pipeline_id,
        store=sql_store,
        broker=rabbitmq_broker,
    )
