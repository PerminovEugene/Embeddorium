"""Fixed-size chunker.

Thin wrapper around ``langchain_text_splitters.CharacterTextSplitter`` with
an empty separator, so it splits purely by character count rather than
looking for a natural break point. The simplest, most predictable strategy
— useful as a baseline or for content with no meaningful structure.
"""

from __future__ import annotations

from typing import List

from langchain_text_splitters import CharacterTextSplitter

from backend.plugins.chunkers._offsets import chunks_with_offsets
from backend.plugins.chunkers._size_fields import size_overlap_fields
from backend.plugins.chunkers.base import Chunk, Chunker, ChunkerConfig, ChunkInput


class FixedSizeChunker(Chunker):
    """Splits text into fixed-size character chunks, ignoring structure."""

    config = ChunkerConfig(
        name="text_fixed",
        label="Fixed size",
        description=(
            "Splits into fixed-size character chunks with no regard for "
            "structure. The simplest, most predictable strategy."
        ),
        fields=size_overlap_fields(),
    )

    def chunk(self, ctx: ChunkInput) -> List[Chunk]:
        if not ctx.text:
            return []
        splitter = CharacterTextSplitter(
            chunk_size=int(self._get("chunk_size")),
            chunk_overlap=int(self._get("chunk_overlap")),
            separator="",
            add_start_index=True,
        )
        return chunks_with_offsets(splitter, ctx.text)
