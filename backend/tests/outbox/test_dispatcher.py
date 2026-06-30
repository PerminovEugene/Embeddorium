import uuid
from unittest.mock import MagicMock

import dramatiq

from backend.shared.models import OutboxEvent
from backend.outbox.dispatcher import dispatch_once


def _event(**kw) -> OutboxEvent:
    return OutboxEvent(
        id=kw.get("id", uuid.uuid4()),
        queue_name=kw.get("queue_name", "laws.crawl.source.parse.v1"),
        actor_name=kw.get("actor_name", "parse_source"),
        payload=kw.get("payload", {"crawl_target_id": "t", "group": "Estonia"}),
        dedup_key=kw.get("dedup_key", "parse:t"),
    )


def test_publishes_pending_events_and_marks_sent():
    e1, e2 = _event(dedup_key="a"), _event(dedup_key="b")
    store = MagicMock()
    store.outbox.list_pending.return_value = [e1, e2]
    broker = MagicMock()

    sent = dispatch_once(store, broker)

    assert sent == 2
    messages = [c.args[0] for c in broker.enqueue.call_args_list]
    assert all(isinstance(m, dramatiq.Message) for m in messages)
    assert messages[0].queue_name == e1.queue_name
    assert messages[0].actor_name == e1.actor_name
    assert messages[0].kwargs == e1.payload
    assert [c.args[0] for c in store.outbox.mark_sent.call_args_list] == [e1.id, e2.id]


def test_publish_failure_records_attempt_and_does_not_mark_sent():
    event = _event()
    store = MagicMock()
    store.outbox.list_pending.return_value = [event]
    broker = MagicMock()
    broker.enqueue.side_effect = RuntimeError("broker down")

    sent = dispatch_once(store, broker)

    assert sent == 0
    store.outbox.mark_sent.assert_not_called()
    store.outbox.record_attempt.assert_called_once_with(event.id)
