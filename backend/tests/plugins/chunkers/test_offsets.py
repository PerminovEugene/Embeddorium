"""Offset tracking for the fixed-size and recursive chunkers.

Both wrap langchain splitters whose chunks are exact substrings of the
input, so ``text[start_offset:end_offset]`` must reproduce each chunk.
"""

from __future__ import annotations

from backend.plugins.chunkers.base import ChunkInput
from backend.plugins.chunkers.text_fixed import FixedSizeChunker
from backend.plugins.chunkers.text_recursive import RecursiveChunker

_TEXT = "abcdefghij klmnopqrst uvwxyz 0123456789\n\nsecond paragraph of text here"


def test_fixed_size_chunks_carry_exact_offsets():
    chunker = FixedSizeChunker({"chunk_size": 10, "chunk_overlap": 3})
    chunks = chunker.chunk(ChunkInput(text=_TEXT))

    assert len(chunks) > 1
    for c in chunks:
        assert c.start_offset is not None and c.end_offset is not None
        assert _TEXT[c.start_offset : c.end_offset] == c.text


def test_recursive_chunks_carry_exact_offsets():
    chunker = RecursiveChunker({"chunk_size": 25, "chunk_overlap": 0})
    chunks = chunker.chunk(ChunkInput(text=_TEXT))

    assert len(chunks) > 1
    for c in chunks:
        assert c.start_offset is not None and c.end_offset is not None
        assert _TEXT[c.start_offset : c.end_offset] == c.text
