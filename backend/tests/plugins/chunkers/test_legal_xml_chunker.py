"""Tests for the legal_xml chunker plugin: happy path + the markdown fallback."""

from __future__ import annotations

from pathlib import Path

from backend.plugins.chunkers.base import ChunkInput
from backend.plugins.chunkers.legal_xml import LegalXmlChunkerPlugin

FIXTURES = Path(__file__).parent.parent.parent / "parsers" / "fixtures"
PORTS_ACT_XML = (FIXTURES / "ports_act_sample.xml").read_text(encoding="utf-8")


def test_parses_act_xml_into_legal_body_chunks():
    chunker = LegalXmlChunkerPlugin({})
    ctx = ChunkInput(
        text="fallback text should not be used",
        raw_content=PORTS_ACT_XML,
        source_url="https://riigiteataja.ee/ports",
    )
    chunks = chunker.chunk(ctx)

    assert chunks
    types = {c.chunk_type for c in chunks}
    assert "legal_body" in types
    assert "act_title" in types
    # link extraction moved to the actor: chunks carry no `links` attribute.
    assert not hasattr(chunks[0], "links")


def test_falls_back_to_markdown_when_raw_content_missing():
    chunker = LegalXmlChunkerPlugin({})
    ctx = ChunkInput(text="Plain markdown text with no XML at all.", raw_content=None)
    chunks = chunker.chunk(ctx)

    assert len(chunks) == 1
    assert chunks[0].text == "Plain markdown text with no XML at all."
    assert chunks[0].chunk_type == "passage"


def test_falls_back_to_markdown_when_raw_content_not_parseable_xml():
    chunker = LegalXmlChunkerPlugin({})
    ctx = ChunkInput(
        text="Plain markdown fallback text.",
        raw_content="not valid xml at all <<<",
    )
    chunks = chunker.chunk(ctx)

    assert len(chunks) == 1
    assert chunks[0].text == "Plain markdown fallback text."


def test_empty_text_and_no_raw_content_returns_no_chunks():
    chunker = LegalXmlChunkerPlugin({})
    chunks = chunker.chunk(ChunkInput(text="", raw_content=None))
    assert chunks == []
