"""Dramatiq launcher for the fetch_source worker (pipeline stage 1)."""

import logging

import dramatiq

from laws_agent.actors.fetch_source_actor.handler import fetch_source as _fetch_source
from laws_agent.clients.http.fetcher import HttpFetcher
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.queue_names import FETCH_SOURCE_ACTOR, FETCH_SOURCE_QUEUE
from laws_agent.logging_config import configure_logging
from laws_agent.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("fetch_source")
dramatiq.set_broker(rabbitmq_broker)

sql_store = SqlStore()
http_fetcher = HttpFetcher()


@dramatiq.actor(
    queue_name=FETCH_SOURCE_QUEUE,
    actor_name=FETCH_SOURCE_ACTOR,
    max_retries=3,
)
def fetch_source(*, crawl_target_id: str, group: str) -> None:
    _fetch_source(
        crawl_target_id=crawl_target_id,
        group=group,
        store=sql_store,
        fetcher=http_fetcher,
    )
