"""Shared result-shaping helpers for the search strategies.

These normalise a retrieval hit into the single result-dict shape returned by
``/search``. They are shared: the keyword and hybrid paths hydrate
``DocumentChunk`` objects through ``result_from_chunk``, while the semantic and
hybrid paths coerce Qdrant payload ids through ``as_uuid``. Anything unique to a
single strategy lives in that strategy's own module instead.
"""

from __future__ import annotations

import uuid


def as_uuid(value) -> uuid.UUID | None:
    """Best-effort parse of a Qdrant payload id into a ``UUID`` (or ``None``)."""
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def result_from_chunk(
    query,
    chunk,
    score,
    dataset_name: str,
) -> dict:
    """Normalise a hydrated ``DocumentChunk`` into a search result dict.

    Shared by the keyword and hybrid paths so both produce the exact same shape
    as the semantic path (which reads ids straight off the Qdrant payload).
    """
    document = chunk.document if chunk else None
    return {
        "source_id": query.id,
        "queryText": query.text,
        "score": score,
        "chunkId": str(chunk.id) if chunk and chunk.id else None,
        "documentId": str(chunk.document_id) if chunk else None,
        "chunkIndex": chunk.chunk_index if chunk else None,
        "group": dataset_name,
        "chunkText": chunk.text if chunk else None,
        "sourceUrl": document.source_url if document else None,
    }
