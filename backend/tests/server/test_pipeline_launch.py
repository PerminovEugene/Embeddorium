"""Tests for _seed_local in pipeline_launch.

Focus: the path-dispatch logic that determines whether a dataset path entry is
treated as an individual XML file or as a directory to glob.

No live broker or DB is required.  The broker is replaced with a MagicMock and
dramatiq.Message is called with the same constants used in production so the
queue/actor name wiring is covered too.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

# Set required env vars before the import pulls in config.py.
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("RABBITMQ_USER", "test")
os.environ.setdefault("RABBITMQ_PASSWORD", "test")

from backend.server.pipeline.launch import _seed_local  # noqa: E402
from backend.shared.clients.queue.queue_names import (  # noqa: E402
    VALIDATE_SOURCE_ACTOR,
    VALIDATE_SOURCE_QUEUE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_broker() -> MagicMock:
    return MagicMock()


def _enqueued_file_paths(broker: MagicMock) -> List[str]:
    """Extract the file-path ``url`` kwarg from every enqueued dramatiq Message."""
    paths = []
    for c in broker.enqueue.call_args_list:
        msg = c[0][0]
        paths.append(msg.kwargs["url"])
    return paths


def _enqueued_queue_names(broker: MagicMock) -> List[str]:
    return [c[0][0].queue_name for c in broker.enqueue.call_args_list]


def _enqueued_actor_names(broker: MagicMock) -> List[str]:
    return [c[0][0].actor_name for c in broker.enqueue.call_args_list]


# ---------------------------------------------------------------------------
# Individual-file paths (the browser file-picker produces these)
# ---------------------------------------------------------------------------


def test_xml_file_path_is_enqueued_directly(tmp_path: Path) -> None:
    """A path entry whose suffix is .xml is enqueued as-is without globbing."""
    xml_file = tmp_path / "501022016017.xml"
    xml_file.touch()

    broker = _make_broker()
    dataset = {"name": "group1", "paths": [str(xml_file)]}
    count = _seed_local(dataset=dataset, pipeline_id_str=str(uuid.uuid4()), broker=broker)

    assert count == 1
    broker.enqueue.assert_called_once()
    assert str(xml_file) in _enqueued_file_paths(broker)


def test_two_xml_file_paths_enqueue_two_messages(tmp_path: Path) -> None:
    """Two individual .xml paths → two enqueued messages."""
    f1 = tmp_path / "501022016016.xml"
    f2 = tmp_path / "501022016017.xml"
    f1.touch()
    f2.touch()

    broker = _make_broker()
    dataset = {"name": "g", "paths": [str(f1), str(f2)]}
    count = _seed_local(dataset=dataset, pipeline_id_str=str(uuid.uuid4()), broker=broker)

    assert count == 2
    assert broker.enqueue.call_count == 2


def test_xml_file_path_not_yet_on_disk_is_still_enqueued() -> None:
    """A .xml path that doesn't yet exist on disk is enqueued anyway.

    The validate_source actor's local strategy rejects missing files with a
    skip. The seeder's job is to dispatch, not to validate local existence.
    """
    broker = _make_broker()
    dataset = {"name": "g", "paths": ["nonexistent_act.xml"]}
    count = _seed_local(dataset=dataset, pipeline_id_str=str(uuid.uuid4()), broker=broker)

    assert count == 1
    broker.enqueue.assert_called_once()


# ---------------------------------------------------------------------------
# Directory paths (admin / API use-case)
# ---------------------------------------------------------------------------


def test_directory_path_globs_xml_children(tmp_path: Path) -> None:
    """A path that resolves to an existing directory enqueues all .xml files in it."""
    (tmp_path / "a.xml").touch()
    (tmp_path / "b.xml").touch()
    (tmp_path / "README.txt").touch()  # non-xml — must be ignored

    broker = _make_broker()
    dataset = {"name": "dir-group", "paths": [str(tmp_path)]}
    count = _seed_local(dataset=dataset, pipeline_id_str=str(uuid.uuid4()), broker=broker)

    assert count == 2
    enqueued = sorted(_enqueued_file_paths(broker))
    assert enqueued == sorted([str(tmp_path / "a.xml"), str(tmp_path / "b.xml")])


def test_directory_path_globs_xml_recursively(tmp_path: Path) -> None:
    """A directory enqueues .xml files in nested subfolders too."""
    (tmp_path / "a.xml").touch()
    nested = tmp_path / "annex"
    nested.mkdir()
    (nested / "b.xml").touch()

    broker = _make_broker()
    dataset = {"name": "g", "paths": [str(tmp_path)]}
    count = _seed_local(dataset=dataset, pipeline_id_str=str(uuid.uuid4()), broker=broker)

    assert count == 2
    enqueued = sorted(_enqueued_file_paths(broker))
    assert enqueued == sorted([str(tmp_path / "a.xml"), str(nested / "b.xml")])


def test_relative_path_is_anchored_to_source_root(
    tmp_path: Path, monkeypatch
) -> None:
    """A source-root-relative path resolves to a real file under the root."""
    (tmp_path / "xml.2026.en").mkdir()
    (tmp_path / "xml.2026.en" / "act.xml").touch()
    monkeypatch.setenv("SOURCE_ROOT", str(tmp_path))

    broker = _make_broker()
    dataset = {"name": "g", "paths": ["xml.2026.en/act.xml"]}
    count = _seed_local(dataset=dataset, pipeline_id_str=str(uuid.uuid4()), broker=broker)

    assert count == 1
    assert _enqueued_file_paths(broker) == [
        str(tmp_path / "xml.2026.en" / "act.xml")
    ]


def test_empty_directory_enqueues_nothing(tmp_path: Path) -> None:
    """A directory with no .xml files yields zero messages."""
    broker = _make_broker()
    dataset = {"name": "g", "paths": [str(tmp_path)]}
    count = _seed_local(dataset=dataset, pipeline_id_str=str(uuid.uuid4()), broker=broker)

    assert count == 0
    broker.enqueue.assert_not_called()


# ---------------------------------------------------------------------------
# Unknown / unrecognised paths
# ---------------------------------------------------------------------------


def test_non_xml_non_directory_path_logs_warning_and_skips(tmp_path: Path) -> None:
    """A path that isn't .xml and isn't a directory logs a warning and is skipped."""
    bogus = str(tmp_path / "not_a_dir_or_xml")  # neither .xml suffix nor dir

    broker = _make_broker()
    dataset = {"name": "g", "paths": [bogus]}
    with patch("backend.server.pipeline.launch.logger") as mock_logger:
        count = _seed_local(dataset=dataset, pipeline_id_str=str(uuid.uuid4()), broker=broker)

    assert count == 0
    broker.enqueue.assert_not_called()
    mock_logger.warning.assert_called_once()


def test_empty_paths_returns_zero() -> None:
    """An empty paths list enqueues nothing and returns 0."""
    broker = _make_broker()
    count = _seed_local(
        dataset={"name": "g", "paths": []},
        pipeline_id_str=str(uuid.uuid4()),
        broker=broker,
    )
    assert count == 0
    broker.enqueue.assert_not_called()


# ---------------------------------------------------------------------------
# Queue / actor name wiring
# ---------------------------------------------------------------------------


def test_enqueued_message_targets_correct_queue_and_actor() -> None:
    """Messages are dispatched to VALIDATE_SOURCE_QUEUE / VALIDATE_SOURCE_ACTOR."""
    broker = _make_broker()
    dataset = {"name": "g", "paths": ["my_act.xml"]}
    _seed_local(dataset=dataset, pipeline_id_str=str(uuid.uuid4()), broker=broker)

    assert _enqueued_queue_names(broker) == [VALIDATE_SOURCE_QUEUE]
    assert _enqueued_actor_names(broker) == [VALIDATE_SOURCE_ACTOR]


def test_pipeline_id_propagated_to_message_kwargs() -> None:
    """The pipeline_id string is forwarded into the message kwargs."""
    broker = _make_broker()
    run_id = str(uuid.uuid4())
    dataset = {"name": "g", "paths": ["act.xml"]}
    _seed_local(dataset=dataset, pipeline_id_str=run_id, broker=broker)

    msg = broker.enqueue.call_args[0][0]
    assert msg.kwargs["pipeline_id"] == run_id
