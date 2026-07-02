"""Shared ``chunk_size``/``chunk_overlap`` field declaration.

The three size-based text chunkers (``text_markdown``, ``text_recursive``,
``text_fixed``) all expose the same pair of UI-configurable numbers with the
same keys, so their :class:`~backend.plugins.chunkers.base.ChunkerConfig`
declarations share this helper instead of repeating the boilerplate three
times.
"""

from __future__ import annotations

from typing import List

from backend.plugins.chunkers.base import ChunkerField
from backend.shared.parsers.chunking_config import CHUNK_OVERLAP, CHUNK_SIZE


def size_overlap_fields(
    *, default_size: int = CHUNK_SIZE, default_overlap: int = CHUNK_OVERLAP
) -> List[ChunkerField]:
    """Return the standard ``chunk_size``/``chunk_overlap`` field pair."""
    return [
        ChunkerField(
            key="chunk_size",
            label="Chunk size",
            type="number",
            default=default_size,
            min=1,
        ),
        ChunkerField(
            key="chunk_overlap",
            label="Chunk overlap",
            type="number",
            default=default_overlap,
            min=0,
        ),
    ]
