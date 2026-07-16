"""Semantic (dense-vector) retrieval strategy for one query.

The default ``/search`` path: ask Qdrant for the nearest vectors in the run's
collection, then join each hit back to Postgres for chunk text and document
metadata. No fusion — Qdrant's own similarity score is the result score.
"""

from __future__ import annotations

from backend.server.search.service.results import as_uuid
from backend.shared.storage.sql.sql_store import SqlStore
from backend.shared.storage.vector.vector_store import VectorStore


def semantic_search(
    store_sql: SqlStore,
    store: VectorStore,
    query,
    embedding: list,
    top_k: int,
    pipeline_id: str,
    dataset_name: str,
) -> list[dict]:
    """Dense nearest-neighbour retrieval for one query.

    Asks Qdrant for the nearest ``top_k`` vectors in the run's collection, then
    joins each hit back to Postgres for chunk text and document metadata. The
    score is Qdrant's similarity score (higher is better, unchanged).
    """
    hits = store.search(embedding, top_k=top_k, pipeline_id=pipeline_id)

    # One batched Postgres round-trip per query instead of one per hit.
    chunk_ids = [as_uuid(hit.get("chunk_id")) for hit in hits if hit.get("chunk_id")]
    chunks_by_id = {
        str(chunk.id): chunk
        for chunk in store_sql.chunks.get_many([c for c in chunk_ids if c])
    }

    query_results: list[dict] = []
    for hit in hits:
        chunk_id = hit.get("chunk_id")
        chunk = chunks_by_id.get(str(chunk_id)) if chunk_id else None
        document = chunk.document if chunk else None

        query_results.append(
            {
                "source_id": query.id,
                "queryText": query.text,
                "score": hit.get("score"),
                "chunkId": chunk_id,
                "documentId": hit.get("document_id"),
                "chunkIndex": hit.get("chunk_index"),
                "group": dataset_name,
                "chunkText": chunk.text if chunk else None,
                "sourceUrl": document.source_url if document else None,
                "metadata": (
                    dict(getattr(chunk, "chunk_metadata", {}) or {}) if chunk else {}
                ),
            }
        )
    return query_results
