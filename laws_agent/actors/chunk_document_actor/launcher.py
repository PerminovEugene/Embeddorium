"""Dramatiq launcher for the chunk_document worker (pipeline stage 3)."""

import logging

import dramatiq

from laws_agent.actors.chunk_document_actor.handler import (
    chunk_document as _chunk_document,
)
from laws_agent.clients.queue.queue_client import QueueClient
from laws_agent.clients.queue.queue_names import (
    CHUNK_DOCUMENT_ACTOR,
    CHUNK_DOCUMENT_QUEUE,
)
from laws_agent.logging_config import configure_logging
from laws_agent.parsers.text_splitter import TextSplitter
from laws_agent.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("chunk_document")
dramatiq.set_broker(rabbitmq_broker)

sql_store = SqlStore()
splitter = TextSplitter()


@dramatiq.actor(
    queue_name=CHUNK_DOCUMENT_QUEUE,
    actor_name=CHUNK_DOCUMENT_ACTOR,
    max_retries=3,
)
def chunk_document(*, crawl_target_id: str, group: str) -> None:
    _chunk_document(
        crawl_target_id=crawl_target_id,
        group=group,
        store=sql_store,
        splitter=splitter,
    )
