"""Shared helper: run a langchain splitter and keep character offsets.

The langchain splitters used by the fixed/recursive/markdown chunkers emit
chunks that are exact substrings of the input, and ``add_start_index=True``
makes ``create_documents`` record where each chunk starts. This helper wraps
that into our plugin :class:`~backend.plugins.chunkers.base.Chunk` type with
``start_offset``/``end_offset`` populated (start inclusive, end exclusive).

Callers must construct their splitter with ``add_start_index=True``.
"""

from __future__ import annotations

from typing import List

from langchain_text_splitters import TextSplitter

from backend.plugins.chunkers.base import Chunk


def chunks_with_offsets(splitter: TextSplitter, text: str) -> List[Chunk]:
    """Split *text* with *splitter*, returning chunks carrying offsets."""
    chunks: List[Chunk] = []
    for doc in splitter.create_documents([text]):
        start = doc.metadata.get("start_index")
        # langchain reports -1 when it could not locate the chunk; treat
        # that as "unknown" rather than storing a bogus offset.
        if start is None or start < 0:
            chunks.append(Chunk(text=doc.page_content))
            continue
        chunks.append(
            Chunk(
                text=doc.page_content,
                start_offset=start,
                end_offset=start + len(doc.page_content),
            )
        )
    return chunks
