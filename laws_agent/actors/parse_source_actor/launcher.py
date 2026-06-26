"""Dramatiq launcher for the parse_source worker (pipeline stage 2)."""

import logging
import uuid

import dramatiq

from laws_agent.actors.parse_source_actor.handler import parse_source as _parse_source
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.queue_names import PARSE_SOURCE_ACTOR, PARSE_SOURCE_QUEUE
from laws_agent.log_routing import log_to
from laws_agent.logging_config import configure_logging
from laws_agent.storage.sql.core.engine import SqlPoolConfig
from laws_agent.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("parse_source")
dramatiq.set_broker(rabbitmq_broker)

# pool_size=2, max_overflow=3: dramatiq gives this worker its own concurrency
# via processes/threads, so the pool only needs to satisfy one process's
# threads, not the whole worker. See SqlPoolConfig for the full reasoning.
sql_store = SqlStore(
    pool_config=SqlPoolConfig(pool_size=2, max_overflow=3),
    application_name=PARSE_SOURCE_ACTOR,
)


@dramatiq.actor(
    queue_name=PARSE_SOURCE_QUEUE,
    actor_name=PARSE_SOURCE_ACTOR,
    max_retries=3,
)
def parse_source(*, crawl_target_id: str, group: str) -> None:
    target = sql_store.crawl_targets.get(uuid.UUID(crawl_target_id))
    log_dir = target.log_dir if target is not None else None

    with log_to(log_dir):
        _parse_source(crawl_target_id=crawl_target_id, group=group, store=sql_store)
