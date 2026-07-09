"""Tests for the default text_markdown chunker."""

from __future__ import annotations

from backend.plugins.chunkers.base import Chunk, ChunkInput
from backend.plugins.chunkers.text_markdown import MarkdownChunker


def test_empty_text_returns_no_chunks():
    chunker = MarkdownChunker({})
    assert chunker.chunk(ChunkInput(text="")) == []


def test_splits_long_text_into_multiple_chunks():
    chunker = MarkdownChunker({"chunk_size": 100, "chunk_overlap": 0})
    long_text = "Word " * 500
    chunks = chunker.chunk(ChunkInput(text=long_text))

    assert len(chunks) > 1
    assert all(isinstance(c, Chunk) for c in chunks)
    for c in chunks:
        assert c.chunk_type == "passage"
        assert c.metadata == {}


def test_short_text_returns_single_chunk():
    chunker = MarkdownChunker({"chunk_size": 1200, "chunk_overlap": 150})
    chunks = chunker.chunk(ChunkInput(text="A short paragraph."))
    assert len(chunks) == 1
    assert chunks[0].text == "A short paragraph."


def test_uses_declared_defaults_when_settings_omitted():
    chunker = MarkdownChunker({})
    assert chunker.settings["chunk_size"] == 1200
    assert chunker.settings["chunk_overlap"] == 150


def test_chunks_carry_source_offsets():
    text = "# Title\n\npara one here now\n\npara two follows here"
    chunker = MarkdownChunker({"chunk_size": 20, "chunk_overlap": 0})
    chunks = chunker.chunk(ChunkInput(text=text))

    assert len(chunks) > 1
    for c in chunks:
        assert c.start_offset is not None and c.end_offset is not None
        # Offsets point at the exact slice of the source the chunk came from.
        assert text[c.start_offset : c.end_offset] == c.text
