"""Tests for source-root resolution and the /source-files browse endpoint.

Covers the path-mapping fix: the UI browses the source tree server-side and
stores paths relative to the source root, which the seeder anchors back onto
that root. No DB or broker is needed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Required before importing config-pulling modules (mirrors test_pipeline_launch).
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("RABBITMQ_USER", "test")
os.environ.setdefault("RABBITMQ_PASSWORD", "test")

from fastapi.testclient import TestClient  # noqa: E402

from backend.server.source_files import source_root  # noqa: E402
from backend.server.source_files.router import router  # noqa: E402
from fastapi import FastAPI  # noqa: E402


@pytest.fixture
def source_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A source root with a nested folder of .xml files plus noise."""
    (tmp_path / "act_root.xml").touch()
    (tmp_path / "notes.txt").touch()
    nested = tmp_path / "xml.2026.en"
    nested.mkdir()
    (nested / "a.xml").touch()
    (nested / "b.xml").touch()
    deeper = nested / "annex"
    deeper.mkdir()
    (deeper / "c.xml").touch()
    monkeypatch.setenv("SOURCE_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(source_tree: Path) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# --- source_root resolution ------------------------------------------------


def test_resolve_for_seed_joins_relative_onto_root(source_tree: Path) -> None:
    resolved = source_root.resolve_for_seed("xml.2026.en/a.xml")
    assert resolved == source_tree / "xml.2026.en" / "a.xml"


def test_resolve_for_seed_passes_absolute_through(source_tree: Path) -> None:
    abs_path = "/somewhere/else/act.xml"
    assert source_root.resolve_for_seed(abs_path) == Path(abs_path)


def test_safe_resolve_rejects_traversal(source_tree: Path) -> None:
    with pytest.raises(ValueError):
        source_root.safe_resolve_within_root("../escape.xml")


def test_safe_resolve_allows_root(source_tree: Path) -> None:
    assert source_root.safe_resolve_within_root("") == source_tree


# --- browse endpoint -------------------------------------------------------


def test_list_root_shows_dirs_and_xml_only(client: TestClient) -> None:
    body = client.get("/source-files").json()
    assert body["path"] == ""
    assert body["parent"] is None
    names = [(e["name"], e["type"]) for e in body["entries"]]
    # Dir first, then the .xml file; the .txt is hidden.
    assert ("xml.2026.en", "dir") in names
    assert ("act_root.xml", "file") in names
    assert all(not n.endswith(".txt") for n, _ in names)


def test_list_nested_dir_sets_parent_and_relative_paths(client: TestClient) -> None:
    body = client.get("/source-files", params={"path": "xml.2026.en"}).json()
    assert body["path"] == "xml.2026.en"
    assert body["parent"] == ""
    paths = {e["path"] for e in body["entries"]}
    assert "xml.2026.en/a.xml" in paths
    assert "xml.2026.en/annex" in paths


def test_list_rejects_traversal(client: TestClient) -> None:
    assert client.get("/source-files", params={"path": "../"}).status_code == 400


def test_list_missing_dir_404(client: TestClient) -> None:
    assert client.get("/source-files", params={"path": "nope"}).status_code == 404
