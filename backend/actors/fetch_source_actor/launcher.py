"""Dramatiq launcher for the merged fetch_source worker (pipeline stage 1).

Serves both ingestion chains: the handler picks a fetch strategy plugin (web
HTTP fetch vs local file read) per the run's dataset source type.
"""

import logging
import uuid
from typing import Optional

import dramatiq

from backend.actors.fetch_source_actor.handler import fetch_source as _fetch_source
from backend.shared.clients.http.fetcher import HttpFetcher
from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.clients.queue.queue_names import FETCH_SOURCE_ACTOR, FETCH_SOURCE_QUEUE
from backend.shared.log_routing import log_to
from backend.shared.logging_config import configure_logging
from backend.shared.storage.sql.core.engine import SqlPoolConfig
from backend.shared.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("fetch_source")
dramatiq.set_broker(rabbitmq_broker)

# pool_size=2, max_overflow=3: dramatiq gives this worker its own concurrency
# via processes/threads, so the pool only needs to satisfy one process's
# threads, not the whole worker. See SqlPoolConfig for the full reasoning.
sql_store = SqlStore(
    pool_config=SqlPoolConfig(pool_size=2, max_overflow=3),
    application_name=FETCH_SOURCE_ACTOR,
)
http_fetcher = HttpFetcher()


@dramatiq.actor(
    queue_name=FETCH_SOURCE_QUEUE,
    actor_name=FETCH_SOURCE_ACTOR,
    max_retries=3,
)
def fetch_source(
    *, crawl_target_id: str, pipeline_id: Optional[str] = None
) -> None:
    target = sql_store.crawl_targets.get(uuid.UUID(crawl_target_id))
    log_dir = target.log_dir if target is not None else None

    with log_to(log_dir, pipeline_id=pipeline_id):
        _fetch_source(
            crawl_target_id=crawl_target_id,
            pipeline_id=pipeline_id,
            store=sql_store,
            fetcher=http_fetcher,
        )
