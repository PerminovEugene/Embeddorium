"""Default chunker: size-based, markdown-aware splitting.

Thin wrapper around ``langchain_text_splitters.MarkdownTextSplitter`` — the
same splitter the legacy ``TextSplitter(strategy="markdown")`` path used, so
selecting this chunker reproduces today's default chunking behavior exactly.
"""

from __future__ import annotations

from typing import List

from langchain_text_splitters import MarkdownTextSplitter

from backend.plugins.chunkers._offsets import chunks_with_offsets
from backend.plugins.chunkers._size_fields import size_overlap_fields
from backend.plugins.chunkers.base import Chunk, Chunker, ChunkerConfig, ChunkInput


class MarkdownChunker(Chunker):
    """Splits text into roughly fixed-size chunks along markdown-aware
    boundaries (headings, paragraphs, sentences, words — in that priority
    order). The default chunker: a reasonable, content-agnostic choice for
    any markdown/plain-text document."""

    config = ChunkerConfig(
        name="text_markdown",
        label="Markdown (size-based)",
        description=(
            "Splits text into roughly fixed-size chunks along markdown-aware "
            "boundaries (headings, paragraphs, sentences). Good general-"
            "purpose default for markdown or plain text."
        ),
        fields=size_overlap_fields(),
    )

    def chunk(self, ctx: ChunkInput) -> List[Chunk]:
        if not ctx.text:
            return []
        splitter = MarkdownTextSplitter(
            chunk_size=int(self._get("chunk_size")),
            chunk_overlap=int(self._get("chunk_overlap")),
            add_start_index=True,
        )
        return chunks_with_offsets(splitter, ctx.text)
