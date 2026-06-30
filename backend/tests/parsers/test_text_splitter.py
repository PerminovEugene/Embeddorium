"""Tests for TextSplitter, covering the section strategy and the default path."""

import pytest

from backend.shared.parsers.text_splitter import Chunk, TextSplitter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _texts(chunks: list) -> list:
    return [c.text for c in chunks]


# ---------------------------------------------------------------------------
# strategy="section" — markdown-header splitting
# ---------------------------------------------------------------------------

MULTIHEADER_MD = """\
# Introduction

Some intro text here.

## Background

Details about background.

### Sub-topic

A sub-topic paragraph.

## Conclusion

Wrapping up.
"""


def test_section_strategy_splits_on_headers():
    splitter = TextSplitter(strategy="section")
    chunks = splitter.split(MULTIHEADER_MD)

    # Expect one chunk per header region (4 headers in the document)
    assert len(chunks) == 4
    # Each chunk should contain its heading
    texts = _texts(chunks)
    assert any("Introduction" in t for t in texts)
    assert any("Background" in t for t in texts)
    assert any("Sub-topic" in t or "Sub" in t for t in texts)
    assert any("Conclusion" in t for t in texts)


def test_section_strategy_keeps_heading_in_chunk_text():
    splitter = TextSplitter(strategy="section")
    chunks = splitter.split(MULTIHEADER_MD)

    texts = _texts(chunks)
    # strip_headers=False means the heading line is preserved
    assert any(t.startswith("# ") for t in texts)
    assert any("## Background" in t for t in texts)


def test_section_strategy_each_chunk_has_link_extraction():
    md = """\
# Section A

See [Docs](https://example.com/docs) for details.

## Section B

No links here.
"""
    splitter = TextSplitter(strategy="section")
    chunks = splitter.split(md)

    # Section A chunk should have one extracted link
    section_a = next(c for c in chunks if "Section A" in c.text)
    assert len(section_a.links) == 1
    assert section_a.links[0]["url"] == "https://example.com/docs"

    section_b = next(c for c in chunks if "Section B" in c.text)
    assert len(section_b.links) == 0


# ---------------------------------------------------------------------------
# strategy="section" — header-less text falls back to paragraphs
# ---------------------------------------------------------------------------

HEADERLESS_TEXT = """\
First paragraph spans
multiple lines here.

Second paragraph is here.

Third paragraph.
"""


def test_section_strategy_headerless_falls_back_to_paragraphs():
    splitter = TextSplitter(strategy="section")
    chunks = splitter.split(HEADERLESS_TEXT)

    texts = _texts(chunks)
    assert len(texts) == 3
    assert any("First paragraph" in t for t in texts)
    assert any("Second paragraph" in t for t in texts)
    assert any("Third paragraph" in t for t in texts)


def test_section_strategy_headerless_single_paragraph():
    text = "Just one paragraph with no blank lines or headers."
    splitter = TextSplitter(strategy="section")
    chunks = splitter.split(text)

    assert len(chunks) == 1
    assert chunks[0].text == text


# ---------------------------------------------------------------------------
# strategy="section" — edge cases
# ---------------------------------------------------------------------------

def test_section_strategy_empty_string_returns_no_chunks():
    splitter = TextSplitter(strategy="section")
    assert splitter.split("") == []


def test_section_strategy_whitespace_only_returns_no_chunks():
    splitter = TextSplitter(strategy="section")
    chunks = splitter.split("   \n\n   ")
    # All chunks should be non-empty after stripping; empty text returns []
    assert all(c.text.strip() for c in chunks)


# ---------------------------------------------------------------------------
# Default / size-based strategies still work
# ---------------------------------------------------------------------------

def test_default_markdown_strategy_produces_size_based_chunks():
    # Generate text long enough to exceed a tiny chunk_size.
    long_text = "Word " * 500
    splitter = TextSplitter(strategy="markdown", chunk_size=100, chunk_overlap=0)
    chunks = splitter.split(long_text)

    assert len(chunks) > 1
    for chunk in chunks:
        # Each chunk must be at most a reasonable multiple of chunk_size
        assert len(chunk.text) <= 300


def test_recursive_strategy_uses_size_based_splitter():
    long_text = "Token " * 400
    splitter = TextSplitter(strategy="recursive", chunk_size=80, chunk_overlap=0)
    chunks = splitter.split(long_text)

    assert len(chunks) > 1


def test_unknown_strategy_falls_back_to_size_based():
    long_text = "Chunk " * 400
    splitter = TextSplitter(strategy="unknown_value", chunk_size=80, chunk_overlap=0)
    chunks = splitter.split(long_text)

    assert len(chunks) > 1


def test_default_strategy_empty_string_returns_no_chunks():
    splitter = TextSplitter()
    chunks = splitter.split("")
    assert chunks == []
