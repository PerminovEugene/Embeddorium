from pathlib import Path

from laws_agent.parsers.xml_parser import XmlParser, extract_act_title

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_extract_act_title_returns_pealkiri_text():
    content = _load_fixture("sample_act.xml")

    assert extract_act_title(content) == "Land Tax Act"


def test_extract_act_title_returns_empty_string_when_missing():
    content = "<oigusakt xmlns='Juurakt'><sisu>no title here</sisu></oigusakt>"

    assert extract_act_title(content) == ""


def test_extract_act_title_returns_empty_string_on_malformed_xml():
    assert extract_act_title("<not <valid xml") == ""


def test_parser_includes_title_as_heading():
    content = _load_fixture("sample_act.xml")

    text = XmlParser().parse(content)

    assert text.startswith("Land Tax Act")


def test_parser_extracts_body_paragraph_text():
    content = _load_fixture("sample_act.xml")

    text = XmlParser().parse(content)

    assert "Land tax is a tax based on the taxable value of land." in text
    assert "Object of taxation" in text
    assert "Land tax is imposed on all land" in text


def test_parser_collapses_whitespace():
    content = _load_fixture("sample_act.xml")

    text = XmlParser().parse(content)

    assert "  " not in text
    assert "\t" not in text


def test_parser_does_not_raise_on_malformed_xml():
    text = XmlParser().parse("<not <valid xml")

    assert text == "<not <valid xml"


def test_parser_handles_empty_content():
    assert XmlParser().parse("") == ""
