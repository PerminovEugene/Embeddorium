"""Dramatiq launcher for the parse_source worker (pipeline stage 2)."""

import logging

import dramatiq

from laws_agent.actors.parse_source_actor.handler import parse_source as _parse_source
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.queue_names import PARSE_SOURCE_ACTOR, PARSE_SOURCE_QUEUE
from laws_agent.logging_config import configure_logging
from laws_agent.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("parse_source")
dramatiq.set_broker(rabbitmq_broker)

sql_store = SqlStore()


@dramatiq.actor(
    queue_name=PARSE_SOURCE_QUEUE,
    actor_name=PARSE_SOURCE_ACTOR,
    max_retries=3,
)
def parse_source(*, crawl_target_id: str, group: str) -> None:
    _parse_source(crawl_target_id=crawl_target_id, group=group, store=sql_store)
