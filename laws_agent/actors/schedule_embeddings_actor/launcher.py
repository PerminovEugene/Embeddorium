"""Dramatiq launcher for the schedule_embeddings worker (pipeline stage 4)."""

import logging

import dramatiq

from laws_agent.actors.schedule_embeddings_actor.handler import (
    schedule_embeddings as _schedule_embeddings,
)
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.queue_names import (
    SCHEDULE_EMBEDDINGS_ACTOR,
    SCHEDULE_EMBEDDINGS_QUEUE,
)
from laws_agent.logging_config import configure_logging
from laws_agent.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("schedule_embeddings")
dramatiq.set_broker(rabbitmq_broker)

sql_store = SqlStore()


@dramatiq.actor(
    queue_name=SCHEDULE_EMBEDDINGS_QUEUE,
    actor_name=SCHEDULE_EMBEDDINGS_ACTOR,
    max_retries=3,
)
def schedule_embeddings(*, crawl_target_id: str, group: str) -> None:
    _schedule_embeddings(crawl_target_id=crawl_target_id, group=group, store=sql_store)
