"""Dramatiq launcher for the fetch_file_source worker (local XML chain entry)."""

import logging
from typing import Optional

import dramatiq

from backend.actors.fetch_file_source_actor.handler import (
    fetch_file_source as _fetch_file_source,
)
from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.clients.queue.queue_names import (
    FETCH_FILE_SOURCE_ACTOR,
    FETCH_FILE_SOURCE_QUEUE,
)
from backend.shared.log_routing import log_to
from backend.shared.logging_config import configure_logging
from backend.shared.storage.sql.core.engine import SqlPoolConfig
from backend.shared.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("fetch_file_source")
dramatiq.set_broker(rabbitmq_broker)

# pool_size=2, max_overflow=3: dramatiq gives this worker its own concurrency
# via processes/threads, so the pool only needs to satisfy one process's
# threads, not the whole worker. See SqlPoolConfig for the full reasoning.
sql_store = SqlStore(
    pool_config=SqlPoolConfig(pool_size=2, max_overflow=3),
    application_name=FETCH_FILE_SOURCE_ACTOR,
)


@dramatiq.actor(
    queue_name=FETCH_FILE_SOURCE_QUEUE,
    actor_name=FETCH_FILE_SOURCE_ACTOR,
    max_retries=3,
)
def fetch_file_source(
    *, file_path: str, pipeline_id: Optional[str] = None
) -> None:
    # No crawl target exists yet (this actor creates it), so there is no
    # log_dir to pre-resolve here. The handler computes log_dir once the
    # target is created and activates routing itself via `log_to`. We still
    # set pipeline_id in the outer context so the inner log_to call inside
    # the handler inherits the run-scoped base path.
    with log_to(None, pipeline_id=pipeline_id):
        _fetch_file_source(
            file_path=file_path,
            pipeline_id=pipeline_id,
            store=sql_store,
            broker=rabbitmq_broker,
        )
