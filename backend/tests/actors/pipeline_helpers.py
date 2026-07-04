"""Shared helpers for the ingestion-pipeline actor tests.

Every stage handler takes an injected ``store`` (and sometimes a fetcher /
splitter). These helpers build a MagicMock store whose ``unit_of_work()`` behaves
as a context manager yielding an inspectable ``uow`` mock, so tests can assert
exactly which transactional writes a stage performed.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import dramatiq

from backend.shared.models import CrawlTarget, CrawlTargetStatus


def make_target(
    *,
    status: CrawlTargetStatus = CrawlTargetStatus.QUEUED,
    url: str = "https://example.com",
    target_id: uuid.UUID | None = None,
) -> CrawlTarget:
    return CrawlTarget(
        id=target_id or uuid.uuid4(),
        original_url=url,
        normalized_url=url + "/",
        status=status,
    )


def make_store(*, acquired: CrawlTarget | None = None) -> MagicMock:
    """Build a mock store. ``acquired`` is what ``crawl_targets.acquire`` returns
    (None simulates losing the processing lock)."""
    store = MagicMock()
    store.crawl_targets.acquire.return_value = acquired

    uow = MagicMock()
    cm = store.unit_of_work.return_value
    cm.__enter__.return_value = uow
    cm.__exit__.return_value = False
    return store


def uow_of(store: MagicMock) -> MagicMock:
    return store.unit_of_work.return_value.__enter__.return_value


def outbox_events(uow: MagicMock):
    """All OutboxEvent objects passed to uow.add_outbox(...)."""
    return [c.args[0] for c in uow.add_outbox.call_args_list]


def outbox_for_queue(uow: MagicMock, queue: str):
    return [e for e in outbox_events(uow) if e.queue_name == queue]


def published_messages(broker: MagicMock) -> list[dramatiq.Message]:
    return [c.args[0] for c in broker.enqueue.call_args_list]
