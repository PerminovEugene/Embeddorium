"""Tests for the structured legal XML reader (the tree layer)."""

from pathlib import Path

from backend.plugins.chunkers.legal_xml.reader import LegalXmlReader

FIXTURES = Path(__file__).parent.parent.parent / "parsers" / "fixtures"
PORTS = (FIXTURES / "ports_act_sample.xml").read_text(encoding="utf-8")
LAND_TAX = (FIXTURES / "sample_act.xml").read_text(encoding="utf-8")


def _parse_ports():
    return LegalXmlReader().parse(PORTS, source_url="https://riigiteataja.ee/ports")


def test_extracts_title_and_document_id():
    doc = _parse_ports()
    assert doc.title == "Ports Act"
    assert doc.document_id == "517062026001"


def test_metadata_is_separated_from_body():
    doc = _parse_ports()
    assert doc.metadata["publisher"] == "Riigikogu"
    assert doc.metadata["documentKind"] == "seadus"
    assert "schemaLocation" in doc.metadata


def test_sections_carry_chapter_path():
    doc = _parse_ports()
    by_number = {(s.path.chapter_number, s.section_number): s for s in doc.sections}
    assert ("1", "1") in by_number
    assert by_number[("1", "1")].path.chapter_title == "General provisions"
    assert by_number[("2", "4")].title == "Waters and entrances"


def test_subsections_and_clauses_parsed():
    doc = _parse_ports()
    s5 = next(s for s in doc.sections if s.section_number == "5")
    assert len(s5.subsections) == 1
    assert len(s5.subsections[0].clauses) == 3


def test_superscript_in_clause_display_normalized():
    doc = _parse_ports()
    s5 = next(s for s in doc.sections if s.section_number == "5")
    third = s5.subsections[0].clauses[2]
    # "3<sup>1</sup>)" -> "3¹)"
    assert "3¹" in third.display
    assert "<sup>" not in third.display


def test_amendments_collected_separately():
    doc = _parse_ports()
    refs = {a.act_reference for a in doc.amendments}
    assert "131052021001" in refs  # § 4 amendment
    assert "103012022003" in refs  # § 5 clause amendment


def test_body_text_excludes_amendment_markers():
    doc = _parse_ports()
    for section in doc.sections:
        for sub in section.subsections:
            assert "131052021001" not in sub.text
            for clause in sub.clauses:
                assert "103012022003" not in clause.text


def test_land_tax_fixture_parses_sections():
    doc = LegalXmlReader().parse(LAND_TAX)
    assert doc.title == "Land Tax Act"
    assert len(doc.sections) == 2


def test_non_juurakt_xml_returns_none():
    assert LegalXmlReader().parse("<root><a>x</a></root>") is None


def test_malformed_xml_returns_none():
    assert LegalXmlReader().parse("<oigusakt><broken>") is None
