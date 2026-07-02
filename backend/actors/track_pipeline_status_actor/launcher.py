"""Dramatiq launcher for the track_pipeline_status worker.

This worker has no vector/torch dependency and no per-target log routing
concept (it isn't tied to any single ``crawl_target``), so unlike
``embed_chunks_actor`` it logs to the run-level log root only
(``log_to(None, pipeline_id=...)``).
"""

import logging

import dramatiq

from backend.actors.track_pipeline_status_actor.handler import (
    track_pipeline_status as _track_pipeline_status,
)
from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.clients.queue.queue_names import (
    TRACK_PIPELINE_STATUS_ACTOR,
    TRACK_PIPELINE_STATUS_QUEUE,
)
from backend.shared.log_routing import log_to
from backend.shared.logging_config import configure_logging
from backend.shared.storage.sql.core.engine import SqlPoolConfig
from backend.shared.storage.sql.sql_store import SqlStore

configure_logging()

logger = logging.getLogger(__name__)

rabbitmq_broker = QueueClient().create("track_pipeline_status")
dramatiq.set_broker(rabbitmq_broker)

# pool_size=2, max_overflow=3: dramatiq gives this worker its own concurrency
# via processes/threads, so the pool only needs to satisfy one process's
# threads, not the whole worker. See SqlPoolConfig for the full reasoning.
sql_store = SqlStore(
    pool_config=SqlPoolConfig(pool_size=2, max_overflow=3),
    application_name=TRACK_PIPELINE_STATUS_ACTOR,
)


@dramatiq.actor(
    queue_name=TRACK_PIPELINE_STATUS_QUEUE,
    actor_name=TRACK_PIPELINE_STATUS_ACTOR,
    max_retries=3,
)
def track_pipeline_status(*, pipeline_id: str, group: str = "") -> None:
    with log_to(None, pipeline_id=pipeline_id):
        _track_pipeline_status(
            pipeline_id=pipeline_id,
            group=group,
            store=sql_store,
        )
