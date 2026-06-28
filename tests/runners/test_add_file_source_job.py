import json
from pathlib import Path
from unittest.mock import MagicMock

import dramatiq
import pytest

from laws_agent.clients.queue.queue_names import (
    FETCH_FILE_SOURCE_ACTOR,
    FETCH_FILE_SOURCE_QUEUE,
)
from laws_agent.runners.add_file_source_job import main


@pytest.fixture
def xml_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "xml.2026.en"
    directory.mkdir()
    (directory / "501012020001.xml").write_text("<oigusakt/>")
    (directory / "501012020002.xml").write_text("<oigusakt/>")
    (directory / "ignored.txt").write_text("not xml")
    return directory


@pytest.fixture
def config_file(tmp_path: Path, xml_dir: Path) -> Path:
    data = {
        "groups": [
            {
                "name": "Estonia",
                "attributes": {"code": "EE"},
                "sources": [
                    {
                        "description": "Estonian acts XML dump.",
                        "type": "xml",
                        "path": str(xml_dir),
                        "glob": "*.xml",
                    },
                ],
            }
        ]
    }
    path = tmp_path / "config.files.json"
    path.write_text(json.dumps(data))
    return path


def test_enqueues_one_message_per_xml_file(config_file: Path) -> None:
    broker = MagicMock()

    main(str(config_file), broker=broker, store=MagicMock())

    assert broker.enqueue.call_count == 2


def test_enqueued_messages_have_correct_queue_and_actor(config_file: Path) -> None:
    broker = MagicMock()

    main(str(config_file), broker=broker, store=MagicMock())

    for enqueue_call in broker.enqueue.call_args_list:
        message: dramatiq.Message = enqueue_call.args[0]
        assert message.queue_name == FETCH_FILE_SOURCE_QUEUE
        assert message.actor_name == FETCH_FILE_SOURCE_ACTOR


def test_enqueued_messages_have_correct_file_paths_and_group(
    config_file: Path, xml_dir: Path
) -> None:
    broker = MagicMock()

    main(str(config_file), broker=broker, store=MagicMock())

    kwargs_list = [call.args[0].kwargs for call in broker.enqueue.call_args_list]

    file_paths = {kwargs["file_path"] for kwargs in kwargs_list}
    assert file_paths == {
        str(xml_dir / "501012020001.xml"),
        str(xml_dir / "501012020002.xml"),
    }
    assert all(kwargs["group"] == "Estonia" for kwargs in kwargs_list)


def test_ignores_non_xml_files(config_file: Path, xml_dir: Path) -> None:
    broker = MagicMock()

    main(str(config_file), broker=broker, store=MagicMock())

    kwargs_list = [call.args[0].kwargs for call in broker.enqueue.call_args_list]
    assert all(not kwargs["file_path"].endswith(".txt") for kwargs in kwargs_list)


def test_does_not_create_real_broker_when_injected(
    config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from laws_agent.runners import add_file_source_job

    monkeypatch.setattr(
        add_file_source_job,
        "QueueClient",
        lambda: (_ for _ in ()).throw(
            RuntimeError("Should not instantiate QueueClient")
        ),
    )

    broker = MagicMock()
    main(str(config_file), broker=broker, store=MagicMock())

    assert broker.enqueue.call_count == 2


def test_skips_web_sources(tmp_path: Path) -> None:
    data = {
        "groups": [
            {
                "name": "Estonia",
                "attributes": {"code": "EE"},
                "sources": [
                    {"description": "Tax authority", "link": "https://emta.ee"},
                ],
            }
        ]
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))
    broker = MagicMock()

    main(str(path), broker=broker, store=MagicMock())

    broker.enqueue.assert_not_called()
