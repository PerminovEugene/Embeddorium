"""Tests for the text_sentence chunker."""

from __future__ import annotations

from backend.plugins.chunkers.base import Chunk, ChunkInput
from backend.plugins.chunkers.text_sentence import SentenceChunker


def test_empty_text_returns_no_chunks():
    assert SentenceChunker({}).chunk(ChunkInput(text="")) == []
    assert SentenceChunker({}).chunk(ChunkInput(text="   \n  ")) == []


def test_short_text_returns_single_chunk():
    chunker = SentenceChunker({"chunk_size": 1200, "chunk_overlap": 0})
    chunks = chunker.chunk(ChunkInput(text="One sentence. Two sentence."))
    assert len(chunks) == 1
    assert chunks[0].text == "One sentence. Two sentence."


def test_never_splits_a_sentence_across_chunks():
    sentences = [f"This is sentence number {i}." for i in range(20)]
    text = " ".join(sentences)
    chunker = SentenceChunker({"chunk_size": 60, "chunk_overlap": 0})
    chunks = chunker.chunk(ChunkInput(text=text))

    assert len(chunks) > 1
    assert all(isinstance(c, Chunk) for c in chunks)
    # With no overlap and single-space joins, each chunk is a verbatim,
    # sentence-aligned slice of the original text — so it must be a substring
    # and must both start and end on a sentence boundary.
    for c in chunks:
        assert c.text in text
        assert c.text.split(" ", 1)[0].startswith("This")
        assert c.text.endswith(".")


def test_overlap_shares_trailing_sentence_between_chunks():
    text = "Alpha one. Bravo two. Charlie three. Delta four."
    chunker = SentenceChunker({"chunk_size": 22, "chunk_overlap": 12})
    chunks = chunker.chunk(ChunkInput(text=text))

    assert len(chunks) > 1
    # With overlap, the last sentence of a chunk reappears in the next one.
    assert "Bravo two." in chunks[0].text
    assert any("Bravo two." in c.text for c in chunks[1:])


def test_sentence_longer_than_chunk_size_is_kept_whole():
    long_sentence = "word " * 50 + "end."
    chunker = SentenceChunker({"chunk_size": 20, "chunk_overlap": 0})
    chunks = chunker.chunk(ChunkInput(text=long_sentence))
    assert len(chunks) == 1
    assert chunks[0].text == long_sentence.replace("  ", " ").strip()


def test_uses_declared_defaults_when_settings_omitted():
    chunker = SentenceChunker({})
    assert chunker.settings["chunk_size"] == 1200
    assert chunker.settings["chunk_overlap"] == 150
