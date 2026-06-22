"""Dramatiq launcher for the schedule_discovered_links worker (pipeline stage 5)."""

import logging

import dramatiq

from laws_agent.actors.schedule_discovered_links_actor.handler import (
    schedule_discovered_links as _schedule_discovered_links,
)
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.queue_names import (
    SCHEDULE_DISCOVERED_LINKS_ACTOR,
    SCHEDULE_DISCOVERED_LINKS_QUEUE,
)
from laws_agent.logging_config import configure_logging
from laws_agent.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("schedule_discovered_links")
dramatiq.set_broker(rabbitmq_broker)

sql_store = SqlStore()


@dramatiq.actor(
    queue_name=SCHEDULE_DISCOVERED_LINKS_QUEUE,
    actor_name=SCHEDULE_DISCOVERED_LINKS_ACTOR,
    max_retries=3,
)
def schedule_discovered_links(*, crawl_target_id: str, group: str) -> None:
    _schedule_discovered_links(
        crawl_target_id=crawl_target_id, group=group, store=sql_store
    )
