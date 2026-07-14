"""Source files share the run's named folder, and delete sweeps every variant.

``write_source_file`` writes under ``<pipeline_id>__<name>/sources/...`` once the
run name is registered (see :mod:`backend.shared.log_routing`), keeping a run's
sources and logs in one identifiable folder. ``delete_run_files`` globs
``<pipeline_id>*`` so the API server (which never resolves names) still removes
both the named folder and any legacy bare-UUID folder.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.shared import log_routing
from backend.shared.pipeline import source_files


@pytest.fixture(autouse=True)
def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(source_files, "PIPELINE_RUNS_DIR", tmp_path)
    log_routing._pipeline_folder_names.clear()
    yield
    log_routing._pipeline_folder_names.clear()


def test_write_source_file_uses_named_folder(tmp_path: Path) -> None:
    log_routing.register_pipeline_name("run-1", "My Run")

    rel = source_files.write_source_file(
        pipeline_id="run-1",
        source_id="src-9",
        kind="raw",
        content="<x/>",
        extension="xml",
    )

    assert rel == "run-1__my_run/sources/src-9/raw/content.xml"
    assert (tmp_path / rel).read_text() == "<x/>"


def test_write_source_file_falls_back_to_bare_id_when_unregistered(
    tmp_path: Path,
) -> None:
    rel = source_files.write_source_file(
        pipeline_id="run-2",
        source_id="src-1",
        kind="parsed",
        content="text",
        extension="txt",
    )

    assert rel == "run-2/sources/src-1/parsed/content.txt"


def test_delete_run_files_removes_named_and_legacy_folders(tmp_path: Path) -> None:
    pid = "11111111-1111-1111-1111-111111111111"
    other_pid = "22222222-2222-2222-2222-222222222222"

    # This run: a named folder plus a stale bare-UUID folder for the same id.
    named = tmp_path / f"{pid}__my_run"
    legacy = tmp_path / pid
    for base in (named, legacy):
        (base / "logs").mkdir(parents=True)
        (base / "logs" / "a.log").write_text("x")
    # A different run must survive — its UUID is not a prefix of pid.
    other = tmp_path / f"{other_pid}__other"
    other.mkdir()

    source_files.delete_run_files(pid)

    assert not named.exists()
    assert not legacy.exists()
    assert other.exists()
