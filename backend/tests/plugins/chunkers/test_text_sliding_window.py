"""Tests for the text_sliding_window chunker."""

from __future__ import annotations

from backend.plugins.chunkers.base import Chunk, ChunkInput
from backend.plugins.chunkers.text_sliding_window import SlidingWindowChunker


def test_empty_text_returns_no_chunks():
    assert SlidingWindowChunker({}).chunk(ChunkInput(text="")) == []
    assert SlidingWindowChunker({}).chunk(ChunkInput(text="   ")) == []


def test_short_text_returns_single_chunk():
    chunker = SlidingWindowChunker({"window_size": 10, "step_size": 5})
    chunks = chunker.chunk(ChunkInput(text="one two three"))
    assert len(chunks) == 1
    assert chunks[0].text == "one two three"


def test_windows_overlap_when_step_smaller_than_window():
    words = " ".join(str(i) for i in range(10))  # "0 1 2 ... 9"
    chunker = SlidingWindowChunker({"window_size": 4, "step_size": 2})
    chunks = chunker.chunk(ChunkInput(text=words))

    assert all(isinstance(c, Chunk) for c in chunks)
    assert [c.text for c in chunks] == [
        "0 1 2 3",
        "2 3 4 5",
        "4 5 6 7",
        "6 7 8 9",
    ]


def test_windows_tile_without_overlap_when_step_equals_window():
    words = " ".join(str(i) for i in range(6))
    chunker = SlidingWindowChunker({"window_size": 3, "step_size": 3})
    chunks = chunker.chunk(ChunkInput(text=words))
    assert [c.text for c in chunks] == ["0 1 2", "3 4 5"]


def test_does_not_emit_trailing_duplicate_tail():
    # window overshoots the end; only one final chunk reaching the last word.
    words = " ".join(str(i) for i in range(5))
    chunker = SlidingWindowChunker({"window_size": 4, "step_size": 2})
    chunks = chunker.chunk(ChunkInput(text=words))
    assert [c.text for c in chunks] == ["0 1 2 3", "2 3 4"]


def test_uses_declared_defaults_when_settings_omitted():
    chunker = SlidingWindowChunker({})
    assert chunker.settings["window_size"] == 200
    assert chunker.settings["step_size"] == 100


def test_chunks_carry_source_offsets():
    text = "  0 1  2 3 4 5\n6 7   8 9  "
    chunker = SlidingWindowChunker({"window_size": 4, "step_size": 2})
    chunks = chunker.chunk(ChunkInput(text=text))

    assert [c.text for c in chunks] == ["0 1 2 3", "2 3 4 5", "4 5 6 7", "6 7 8 9"]
    # Offsets span from the first word's start to the last word's end in the
    # *original* text, so slicing the source recovers the (un-normalised)
    # window content.
    assert (chunks[0].start_offset, chunks[0].end_offset) == (2, 10)
    assert text[chunks[0].start_offset : chunks[0].end_offset] == "0 1  2 3"
    assert text[chunks[-1].start_offset : chunks[-1].end_offset] == "6 7   8 9"
