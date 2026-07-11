"""Query-building tests for ``ChunkRepository.search_bm25`` run-scoping.

pg_textsearch's ``bm25`` index / ``<@>`` operator isn't available against a
plain in-memory DB, so rather than execute the SQL we intercept the ``Session``
the repository opens and capture the raw statement + bound parameters it would
run. That's enough to prove the ``pipeline_id`` scoping is compiled into the
query (joining ``crawl_targets``) and always *bound*, never string-formatted.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager

from backend.shared.storage.sql.repositories import chunk_repo
from backend.shared.storage.sql.repositories.chunk_repo import ChunkRepository


class _CapturingSession:
    """Stands in for a SQLAlchemy ``Session`` context manager, recording the
    statement/params passed to ``execute`` and returning no rows."""

    def __init__(self) -> None:
        self.statement = None
        self.params = None

    def __enter__(self) -> "_CapturingSession":
        return self

    def __exit__(self, *exc) -> None:
        return None

    def execute(self, statement, params):
        self.statement = statement
        self.params = params
        return _EmptyResult()


class _EmptyResult:
    def all(self) -> list:
        return []


@contextmanager
def _patched_session(monkeypatch):
    captured = _CapturingSession()
    monkeypatch.setattr(chunk_repo, "Session", lambda engine: captured)
    yield captured


def _repo() -> ChunkRepository:
    # engine is never touched: our fake Session ignores it.
    return ChunkRepository(engine=object())


def test_search_bm25_without_pipeline_spans_all_chunks(monkeypatch):
    with _patched_session(monkeypatch) as session:
        result = _repo().search_bm25("hello world", limit=7)

    assert result == []
    sql = str(session.statement)
    assert "crawl_targets" not in sql
    assert "pipeline_id" not in session.params
    assert session.params == {"query": "hello world", "limit": 7}


def test_search_bm25_with_pipeline_scopes_to_run(monkeypatch):
    pipeline_id = uuid.uuid4()
    with _patched_session(monkeypatch) as session:
        result = _repo().search_bm25("hello", limit=5, pipeline_id=pipeline_id)

    assert result == []
    sql = str(session.statement)
    # Scoped to the run's chunks via the crawl_targets join.
    assert "crawl_targets" in sql
    assert "ct.document_id = dc.document_id" in sql
    # pipeline_id is bound (and cast), never interpolated into the SQL.
    assert str(pipeline_id) not in sql
    assert session.params["pipeline_id"] == str(pipeline_id)
    assert session.params["query"] == "hello"
    assert session.params["limit"] == 5
