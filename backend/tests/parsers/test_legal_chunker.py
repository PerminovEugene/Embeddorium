"""Tests for the legal-structure-aware chunker (requirement #10)."""

from pathlib import Path

import pytest

from backend.shared.parsers.legal_chunker import (
    CHUNK_ACT_TITLE,
    CHUNK_AMENDMENT_HISTORY,
    CHUNK_LEGAL_BODY,
    CHUNK_LEGAL_METADATA,
    LegalChunkConfig,
    LegalChunker,
    build_report,
    format_for_inspection,
)
from backend.shared.parsers.legal_xml import LegalXmlReader

FIXTURES = Path(__file__).parent / "fixtures"
PORTS = (FIXTURES / "ports_act_sample.xml").read_text(encoding="utf-8")


def _doc():
    return LegalXmlReader().parse(PORTS, source_url="https://riigiteataja.ee/ports")


def _chunk(config=None):
    return LegalChunker(config or LegalChunkConfig()).chunk(_doc())


def _body(chunks):
    return [c for c in chunks if c.chunk_type == CHUNK_LEGAL_BODY]


# -- requirement #2: no title-only chunks in legal_body ----------------------

def test_no_title_only_legal_body_chunks():
    chunks = _chunk()
    for c in _body(chunks):
        stripped = c.text.strip()
        assert stripped not in {"Ports Act", "Act: Ports Act"}
        assert len(stripped) > len("Act: Ports Act")


# -- requirement #8: separate chunk types ------------------------------------

def test_separate_chunk_types_emitted():
    types = {c.chunk_type for c in _chunk()}
    assert CHUNK_LEGAL_BODY in types
    assert CHUNK_ACT_TITLE in types
    assert CHUNK_LEGAL_METADATA in types
    assert CHUNK_AMENDMENT_HISTORY in types


def test_act_title_is_its_own_chunk_not_searchable_body():
    chunks = _chunk()
    title_chunks = [c for c in chunks if c.chunk_type == CHUNK_ACT_TITLE]
    assert len(title_chunks) == 1
    assert "Ports Act" in title_chunks[0].text


# -- requirement: one normal § -> one chunk ----------------------------------

def test_one_normal_section_becomes_one_chunk():
    # Default limits are generous: § 4 fits in a single chunk.
    body = _body(_chunk(LegalChunkConfig()))
    s4 = [c for c in body if c.metadata.get("sectionNumber") == "4"]
    assert len(s4) == 1
    assert "subsectionRange" not in s4[0].metadata or not s4[0].metadata["subsectionRange"]


# -- requirement #4: long § split by subsection ranges -----------------------

def test_long_section_split_by_subsection_ranges():
    cfg = LegalChunkConfig(target_tokens=70, max_tokens=200, min_tokens=20)
    body = _body(_chunk(cfg))
    s4 = [c for c in body if c.metadata.get("sectionNumber") == "4"]
    assert len(s4) > 1
    for c in s4:
        assert c.metadata.get("subsectionRange")
        assert "Subsections:" in c.text


def test_split_chunks_do_not_exceed_max_tokens():
    cfg = LegalChunkConfig(target_tokens=70, max_tokens=200, min_tokens=20)
    body = _body(_chunk(cfg))
    s4 = [c for c in body if c.metadata.get("sectionNumber") == "4"]
    # With a realistic ceiling each split subsection respects max_tokens.
    for c in s4:
        assert c.token_count <= cfg.max_tokens


# -- requirement #5: heading context preserved in every chunk ----------------

def test_every_legal_body_chunk_repeats_heading_context():
    for c in _body(_chunk()):
        assert c.text.startswith("Act: Ports Act")
        assert "Chapter" in c.text


def test_chapter_title_present_in_chunk_for_chapter_two_sections():
    body = _body(_chunk())
    s4 = next(c for c in body if c.metadata.get("sectionNumber") == "4")
    assert "Water traffic safety" in s4.text


# -- requirement #6/#8: amendment/publication metadata not in legal_body -----

def test_legal_body_does_not_contain_publication_metadata():
    for c in _body(_chunk()):
        assert "131052021001" not in c.text  # § 4 aktViide
        assert "103012022003" not in c.text  # § 5 clause aktViide
        assert "RT I" not in c.text
        assert "joustumine" not in c.text


def test_amendment_history_chunk_does_contain_references():
    chunks = _chunk()
    amend = [c for c in chunks if c.chunk_type == CHUNK_AMENDMENT_HISTORY]
    assert amend
    joined = " ".join(c.text for c in amend)
    assert "131052021001" in joined or "RT I" in joined


# -- requirement #7: chunk metadata fields -----------------------------------

def test_chunk_metadata_has_required_fields():
    body = _body(_chunk())
    s4 = next(c for c in body if c.metadata.get("sectionNumber") == "4")
    for key in ("actTitle", "chapterTitle", "sectionNumber", "sectionTitle", "legalPath"):
        assert key in s4.metadata
    assert s4.metadata["actTitle"] == "Ports Act"
    assert s4.metadata["chunkIndex"] == body.index(s4) if s4 in body else True


def test_chunk_index_is_sequential_and_unique():
    chunks = _chunk()
    indices = [c.metadata["chunkIndex"] for c in chunks]
    assert indices == list(range(len(chunks)))


# -- requirement #6: chunks do not cross chapters ----------------------------

def test_no_chunk_spans_multiple_chapters():
    for c in _body(_chunk()):
        # General provisions vs Water traffic safety must never co-occur.
        assert not (
            "General provisions" in c.text
            and "Water traffic safety" in c.text
        )
        assert "," not in str(c.metadata.get("chapterNumber", ""))


def test_merge_only_joins_same_chapter_short_sections():
    # Tiny min forces §§ 1 and 2 (both very short, chapter 1) to merge.
    cfg = LegalChunkConfig(target_tokens=200, max_tokens=400, min_tokens=200)
    body = _body(_chunk(cfg))
    merged = [c for c in body if c.metadata.get("merged")]
    assert merged
    for c in merged:
        assert c.metadata["chapterNumber"] == "1"
        assert "Water traffic safety" not in c.text


# -- requirement #6: a normal § chunk contains only its own section ----------

def test_normal_section_chunk_contains_single_section():
    body = _body(_chunk())
    s4 = next(c for c in body if c.metadata.get("sectionNumber") == "4")
    # § 4 chunk must not bleed into § 5.
    assert "§ 5." not in s4.text


# -- requirement #11/#12: report + inspection helpers ------------------------

def test_build_report_flags_no_problems_on_default_config():
    chunks = _chunk()
    report = build_report(chunks, min_tokens=20)
    assert report.total == len(chunks)
    assert report.by_type[CHUNK_LEGAL_BODY] >= 1
    assert report.multi_chapter == []
    assert report.metadata_leak == []


def test_format_for_inspection_includes_index_type_and_path():
    text = format_for_inspection(_chunk(), preview=120)
    assert "type=legal_body" in text
    assert "tokens=" in text
    assert "path=" in text


def test_disabling_heading_context_omits_header():
    cfg = LegalChunkConfig(include_heading_context=False)
    body = _body(_chunk(cfg))
    assert not any(c.text.startswith("Act: Ports Act") for c in body)


def test_empty_document_yields_no_body_chunks():
    doc = _doc()
    doc.sections = []
    chunks = LegalChunker().chunk(doc)
    assert _body(chunks) == []
