import logging
import threading
from pathlib import Path

import pytest

from laws_agent import log_routing
from laws_agent.log_routing import (
    ContextRoutingFileHandler,
    build_log_dir,
    log_to,
)


@pytest.fixture
def handler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ContextRoutingFileHandler:
    """A routing handler rooted at a temp dir, isolated from the real LOG_ROOT."""
    monkeypatch.setattr(log_routing, "LOG_ROOT", tmp_path)
    formatter = logging.Formatter("%(message)s")
    handler = ContextRoutingFileHandler(tmp_path, formatter)
    try:
        yield handler
    finally:
        handler.close()


def _emit(handler: ContextRoutingFileHandler, message: str) -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    handler.emit(record)


def _read(tmp_path: Path, log_dir: str) -> str:
    leaf = Path(log_dir).name
    return (tmp_path / log_dir / f"{leaf}.log").read_text()


# --- build_log_dir ---


def test_build_log_dir_slugifies_netloc_and_path() -> None:
    log_dir = build_log_dir(
        url="https://EMTA.ee/Some/Path", normalized_url="https://emta.ee/Some/Path"
    )
    leaf = log_dir.rsplit("-", 1)[0]
    assert leaf == "emta_ee_some_path"


def test_build_log_dir_appends_hash_suffix_for_uniqueness() -> None:
    log_dir = build_log_dir(url="https://emta.ee", normalized_url="https://emta.ee/")
    suffix = log_dir.rsplit("-", 1)[1]
    assert len(suffix) == 8
    assert all(c in "0123456789abcdef" for c in suffix)


def test_build_log_dir_is_deterministic_for_same_normalized_url() -> None:
    first = build_log_dir(url="https://emta.ee", normalized_url="https://emta.ee/")
    second = build_log_dir(url="https://emta.ee", normalized_url="https://emta.ee/")
    assert first == second


def test_build_log_dir_differs_for_different_normalized_urls() -> None:
    first = build_log_dir(url="https://emta.ee/a", normalized_url="https://emta.ee/a")
    second = build_log_dir(url="https://emta.ee/a", normalized_url="https://emta.ee/b")
    assert first != second


def test_build_log_dir_nests_under_parent() -> None:
    parent = build_log_dir(url="https://emta.ee", normalized_url="https://emta.ee/")
    child = build_log_dir(
        url="https://emta.ee/sub-page",
        normalized_url="https://emta.ee/sub-page",
        parent_log_dir=parent,
    )
    assert child.startswith(parent + "/")
    assert child.count("/") == 1


def test_build_log_dir_caps_nesting_depth_without_splitting_names() -> None:
    from laws_agent.log_routing import _MAX_DEPTH

    # A very deep parent chain of complete, valid folder names.
    parent = "/".join(f"level{i}-{i:08d}" for i in range(_MAX_DEPTH + 5))
    child = build_log_dir(
        url="https://emta.ee/leaf",
        normalized_url="https://emta.ee/leaf",
        parent_log_dir=parent,
    )

    components = child.split("/")
    # Depth is capped...
    assert len(components) == _MAX_DEPTH
    # ...the newest folder is the leaf we just built...
    assert components[-1].startswith("emta_ee_leaf-")
    # ...and every surviving component is a whole, un-split folder name (the
    # left-truncation bug used to produce fragments like "evel7-00000007").
    assert all(c.startswith("level") for c in components[:-1])


# --- ContextRoutingFileHandler + log_to: isolation ---


def test_unset_context_writes_no_file(
    handler: ContextRoutingFileHandler, tmp_path: Path
) -> None:
    _emit(handler, "no context active")
    assert list(tmp_path.iterdir()) == []


def test_log_to_writes_record_to_its_own_file(
    handler: ContextRoutingFileHandler, tmp_path: Path
) -> None:
    with log_to("site_a-aaaaaaaa"):
        _emit(handler, "hello from a")

    contents = _read(tmp_path, "site_a-aaaaaaaa")
    assert "hello from a" in contents


def test_log_to_nested_dir_creates_nested_file(
    handler: ContextRoutingFileHandler, tmp_path: Path
) -> None:
    nested = "site_a-aaaaaaaa/sub_page-bbbbbbbb"
    with log_to(nested):
        _emit(handler, "hello from nested page")

    contents = _read(tmp_path, nested)
    assert "hello from nested page" in contents

    # File lives at <root>/<parent>/<child>/<child-leaf>.log, not at the parent.
    leaf = Path(nested).name
    assert (tmp_path / nested / f"{leaf}.log").exists()
    assert not (tmp_path / "site_a-aaaaaaaa" / "site_a-aaaaaaaa.log").exists()


def test_log_to_is_noop_when_log_dir_is_none(
    handler: ContextRoutingFileHandler, tmp_path: Path
) -> None:
    with log_to(None):
        _emit(handler, "should not be written anywhere")
    assert list(tmp_path.iterdir()) == []


def test_context_resets_after_exiting_log_to(
    handler: ContextRoutingFileHandler, tmp_path: Path
) -> None:
    with log_to("site_a-aaaaaaaa"):
        _emit(handler, "inside context")

    _emit(handler, "outside context, should be dropped")

    contents = _read(tmp_path, "site_a-aaaaaaaa")
    assert "outside context, should be dropped" not in contents


def test_sequential_contexts_isolate_records_per_file(
    handler: ContextRoutingFileHandler, tmp_path: Path
) -> None:
    with log_to("dir_a-aaaaaaaa"):
        _emit(handler, "message for a")

    with log_to("dir_b-bbbbbbbb"):
        _emit(handler, "message for b")

    a_contents = _read(tmp_path, "dir_a-aaaaaaaa")
    b_contents = _read(tmp_path, "dir_b-bbbbbbbb")

    assert "message for a" in a_contents
    assert "message for b" not in a_contents
    assert "message for b" in b_contents
    assert "message for a" not in b_contents


def test_concurrent_threads_do_not_leak_records_across_files(
    handler: ContextRoutingFileHandler, tmp_path: Path
) -> None:
    """Two threads run concurrently under different contexts; contextvars are
    per-thread, so each thread's records must land only in its own file."""
    barrier = threading.Barrier(2)

    def worker(log_dir: str, message: str) -> None:
        with log_to(log_dir):
            barrier.wait()  # maximize overlap between the two threads
            for _ in range(20):
                _emit(handler, message)

    thread_a = threading.Thread(
        target=worker, args=("dir_a-aaaaaaaa", "only for a")
    )
    thread_b = threading.Thread(
        target=worker, args=("dir_b-bbbbbbbb", "only for b")
    )

    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    a_contents = _read(tmp_path, "dir_a-aaaaaaaa")
    b_contents = _read(tmp_path, "dir_b-bbbbbbbb")

    assert a_contents.count("only for a") == 20
    assert "only for b" not in a_contents
    assert b_contents.count("only for b") == 20
    assert "only for a" not in b_contents


def test_reused_stream_appends_rather_than_truncates(
    handler: ContextRoutingFileHandler, tmp_path: Path
) -> None:
    with log_to("dir_a-aaaaaaaa"):
        _emit(handler, "first")
        _emit(handler, "second")

    contents = _read(tmp_path, "dir_a-aaaaaaaa")
    assert contents.splitlines() == ["first", "second"]


# --- install_file_routing idempotency ---


def test_install_file_routing_is_idempotent() -> None:
    root = logging.getLogger("test_install_file_routing_is_idempotent")
    formatter = logging.Formatter("%(message)s")

    log_routing.install_file_routing(root, formatter)
    log_routing.install_file_routing(root, formatter)

    routing_handlers = [
        h for h in root.handlers if isinstance(h, ContextRoutingFileHandler)
    ]
    assert len(routing_handlers) == 1

    for h in root.handlers:
        h.close()
