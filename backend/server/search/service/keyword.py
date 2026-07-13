"""Keyword (BM25 sparse) retrieval strategy for one query.

Runs BM25 over the chunk text via ``ChunkRepository.search_bm25``, scoped to the
selected run's chunks. No embedding model is used, so this path never touches
Ollama or Qdrant.
"""

from __future__ import annotations

from backend.server.search.service.results import result_from_chunk
from backend.shared.storage.sql.sql_store import SqlStore


def keyword_search(
    store_sql: SqlStore,
    query,
    top_k: int,
    pipeline_id: str,
    dataset_name: str,
) -> list[dict]:
    """BM25 sparse retrieval for one query, scoped to the run's chunks.

    ``search_bm25`` already returns hydrated ``DocumentChunk`` objects (with
    ``.document``) best-first, so there's no extra Postgres round-trip here. The
    score is the raw BM25 score (a *negated* score — lower/more-negative is a
    better match; see ``search_bm25``). No embedding model is involved in the
    sparse signal.
    """
    hits = store_sql.chunks.search_bm25(
        query.text, limit=top_k, pipeline_id=pipeline_id
    )
    return [
        result_from_chunk(query, chunk, score, dataset_name) for chunk, score in hits
    ]
