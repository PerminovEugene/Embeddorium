import pytest

from backend.shared.parsers.keyword_filter import matches_keywords

_KEYWORDS = ["income", "tax", "customs", "excise", "vat", "levy"]

MATCHING_TITLES = [
    "Value Added Tax Act",
    "Customs Act",
    "Alcohol, Tobacco, Fuel and Electricity Excise Duty Act",
    "Income Tax Act",
    "Social Tax Act",
]

NON_MATCHING_TITLES = [
    "Strategic Goods Act",
    "Aliens Act",
    "Traffic Act",
]


@pytest.mark.parametrize("title", MATCHING_TITLES)
def test_keyword_titles_are_detected(title: str):
    assert matches_keywords(title, keywords=_KEYWORDS) is True


@pytest.mark.parametrize("title", NON_MATCHING_TITLES)
def test_non_keyword_titles_are_not_detected(title: str):
    assert matches_keywords(title, keywords=_KEYWORDS) is False


def test_is_case_insensitive():
    assert matches_keywords("value added TAX act", keywords=["tax"]) is True
    assert matches_keywords("CUSTOMS ACT", keywords=["customs"]) is True


def test_empty_title_falls_back_to_text():
    assert (
        matches_keywords(
            "", text="This document covers income tax regulations.", keywords=["income"]
        )
        is True
    )


def test_empty_title_and_text_returns_false():
    assert matches_keywords("", keywords=["income"]) is False
    assert matches_keywords("", text="", keywords=["income"]) is False
    assert matches_keywords("", text="Aliens Act provisions.", keywords=["income"]) is False


def test_word_boundary_avoids_substring_false_positives():
    # "duty" should not match inside an unrelated longer word.
    assert matches_keywords("Dutyfree Imaginary Word Act", keywords=["duty"]) is False


def test_no_keywords_is_passthrough():
    """Empty or absent keywords → every document is considered relevant."""
    assert matches_keywords("Aliens Act") is True
    assert matches_keywords("Aliens Act", keywords=None) is True
    assert matches_keywords("Aliens Act", keywords=[]) is True
    assert matches_keywords("", keywords=[]) is True
    assert matches_keywords("", text="irrelevant content", keywords=None) is True
