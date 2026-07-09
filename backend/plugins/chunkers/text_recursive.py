"""Recursive-character chunker.

Thin wrapper around ``langchain_text_splitters.RecursiveCharacterTextSplitter``
— tries a prioritized list of separators (paragraph, line, word, character)
recursively until each chunk fits ``chunk_size``. A common general-purpose
alternative to the markdown splitter for non-markdown prose.
"""

from __future__ import annotations

from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.plugins.chunkers._offsets import chunks_with_offsets
from backend.plugins.chunkers._size_fields import size_overlap_fields
from backend.plugins.chunkers.base import Chunk, Chunker, ChunkerConfig, ChunkInput


class RecursiveChunker(Chunker):
    """Splits text by recursively trying paragraph/line/word/character
    separators until each chunk is within ``chunk_size``."""

    config = ChunkerConfig(
        name="text_recursive",
        label="Recursive character",
        description=(
            "Splits by a prioritized list of separators (paragraphs, lines, "
            "words), recursively, until each chunk fits the target size."
        ),
        fields=size_overlap_fields(),
    )

    def chunk(self, ctx: ChunkInput) -> List[Chunk]:
        if not ctx.text:
            return []
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(self._get("chunk_size")),
            chunk_overlap=int(self._get("chunk_overlap")),
            add_start_index=True,
        )
        return chunks_with_offsets(splitter, ctx.text)
