"""Dramatiq launcher for the filter_documents worker (local file chain gate)."""

import logging
import uuid
from typing import Optional

import dramatiq

from backend.actors.filter_documents_actor.handler import (
    filter_documents as _filter_documents,
)
from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.clients.queue.queue_names import (
    FILTER_DOCUMENTS_ACTOR,
    FILTER_DOCUMENTS_QUEUE,
)
from backend.shared.log_routing import log_to
from backend.shared.logging_config import configure_logging
from backend.shared.storage.sql.core.engine import SqlPoolConfig
from backend.shared.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("filter_documents")
dramatiq.set_broker(rabbitmq_broker)

# pool_size=2, max_overflow=3: dramatiq gives this worker its own concurrency
# via processes/threads, so the pool only needs to satisfy one process's
# threads, not the whole worker. See SqlPoolConfig for the full reasoning.
sql_store = SqlStore(
    pool_config=SqlPoolConfig(pool_size=2, max_overflow=3),
    application_name=FILTER_DOCUMENTS_ACTOR,
)


@dramatiq.actor(
    queue_name=FILTER_DOCUMENTS_QUEUE,
    actor_name=FILTER_DOCUMENTS_ACTOR,
    max_retries=3,
)
def filter_documents(
    *, crawl_target_id: str, pipeline_id: Optional[str] = None
) -> None:
    target = sql_store.crawl_targets.get(uuid.UUID(crawl_target_id))
    log_dir = target.log_dir if target is not None else None

    with log_to(log_dir, pipeline_id=pipeline_id):
        _filter_documents(
            crawl_target_id=crawl_target_id,
            pipeline_id=pipeline_id,
            store=sql_store,
        )
