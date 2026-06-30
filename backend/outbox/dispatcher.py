"""Outbox dispatcher.

Polls ``outbox_events`` for pending rows and publishes them to RabbitMQ, marking
each ``sent`` once enqueued. Run as a standalone worker:

    python -m backend.outbox.dispatcher

This is the only component that turns committed outbox rows into queue messages,
so every actor's "write data + enqueue next step" is a single DB transaction
(no dual-write). Delivery is at-least-once; consumers are idempotent
(compare-and-set status locks + dedup keys + upserts), so re-delivery is safe.
"""

from __future__ import annotations

import logging
import time

import dramatiq

from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.logging_config import configure_logging
from backend.shared.storage.sql.core.engine import SqlPoolConfig
from backend.shared.storage.sql.sql_store import SqlStore

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 1.0
DEFAULT_BATCH_LIMIT = 100


def dispatch_once(store: SqlStore, broker, limit: int = DEFAULT_BATCH_LIMIT) -> int:
    """Publish one batch of pending outbox events. Returns the number sent."""
    events = store.outbox.list_pending(limit)
    sent = 0
    for event in events:
        try:
            broker.enqueue(
                dramatiq.Message(
                    queue_name=event.queue_name,
                    actor_name=event.actor_name,
                    args=[],
                    kwargs=event.payload,
                    options={},
                )
            )
        except Exception:
            logger.exception(
                "outbox_publish_failed event_id=%s queue=%s actor=%s",
                event.id,
                event.queue_name,
                event.actor_name,
            )
            store.outbox.record_attempt(event.id)
            continue

        store.outbox.mark_sent(event.id)
        sent += 1
    return sent


def run_forever(poll_interval: float = DEFAULT_POLL_INTERVAL) -> None:
    configure_logging()
    # Single-threaded poll loop (not dramatiq), so one connection is enough;
    # keep a tiny overflow for safety margin without contributing
    # meaningfully to the cluster-wide connection count.
    store = SqlStore(
        pool_config=SqlPoolConfig(pool_size=1, max_overflow=2),
        application_name="outbox_dispatcher",
    )
    broker = QueueClient().create("outbox_dispatcher")
    logger.info("outbox dispatcher started poll_interval=%s", poll_interval)
    while True:
        dispatched = dispatch_once(store, broker)
        # Drain fast under load; back off only when there is nothing to do.
        if dispatched == 0:
            time.sleep(poll_interval)


if __name__ == "__main__":
    run_forever()
