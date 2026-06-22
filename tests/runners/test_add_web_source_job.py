import json
import dramatiq
import pytest
from pathlib import Path
from unittest.mock import MagicMock, call

from laws_agent.clients.queue.queue_names import CRAWL_FRONTIER_MANAGER_QUEUE, CRAWL_FRONTIER_MANAGER_ACTOR
from laws_agent.runners.add_web_source_job import main, ensure_scheme


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    data = {
        "groups": [
            {
                "name": "Estonia",
                "attributes": {"code": "EE"},
                "sources": [
                    {"description": "Tax authority", "link": "https://emta.ee"},
                    {"description": "Laws", "link": "riigiteataja.ee"},
                ],
            },
            {
                "name": "Latvia",
                "attributes": {"code": "LV"},
                "sources": [
                    {"description": "Revenue service", "link": "https://vid.gov.lv"},
                ],
            },
        ]
    }
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(data))
    return path


def test_enqueues_one_message_per_source(config_file: Path) -> None:
    broker = MagicMock()

    main(str(config_file), broker=broker)

    assert broker.enqueue.call_count == 3


def test_enqueued_messages_have_correct_queue_and_actor(config_file: Path) -> None:
    broker = MagicMock()

    main(str(config_file), broker=broker)

    for enqueue_call in broker.enqueue.call_args_list:
        message: dramatiq.Message = enqueue_call.args[0]
        assert message.queue_name == CRAWL_FRONTIER_MANAGER_QUEUE
        assert message.actor_name == CRAWL_FRONTIER_MANAGER_ACTOR


def test_enqueued_messages_have_correct_urls_and_groups(config_file: Path) -> None:
    broker = MagicMock()

    main(str(config_file), broker=broker)

    kwargs_list = [
        call.args[0].kwargs for call in broker.enqueue.call_args_list
    ]

    assert {"url": "https://emta.ee", "group": "Estonia", "parent_document_id": None, "parent_chunk_id": None} in kwargs_list
    assert {"url": "https://riigiteataja.ee", "group": "Estonia", "parent_document_id": None, "parent_chunk_id": None} in kwargs_list
    assert {"url": "https://vid.gov.lv", "group": "Latvia", "parent_document_id": None, "parent_chunk_id": None} in kwargs_list


def test_ensure_scheme_adds_https_when_missing() -> None:
    assert ensure_scheme("example.com") == "https://example.com"


def test_ensure_scheme_preserves_existing_scheme() -> None:
    assert ensure_scheme("https://example.com") == "https://example.com"
    assert ensure_scheme("http://example.com") == "http://example.com"


def test_does_not_create_real_broker_when_injected(config_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from laws_agent.runners import add_web_source_job

    queue_client_called = []
    monkeypatch.setattr(
        add_web_source_job,
        "QueueClient",
        lambda: (_ for _ in ()).throw(RuntimeError("Should not instantiate QueueClient")),
    )

    broker = MagicMock()
    main(str(config_file), broker=broker)

    assert broker.enqueue.call_count == 3
