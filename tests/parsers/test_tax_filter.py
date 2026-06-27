import pytest

from laws_agent.parsers.tax_filter import is_tax_related

TAX_TITLES = [
    "Value Added Tax Act",
    "Customs Act",
    "Alcohol, Tobacco, Fuel and Electricity Excise Duty Act",
    "Income Tax Act",
    "Social Tax Act",
]

NON_TAX_TITLES = [
    "Strategic Goods Act",
    "Aliens Act",
    "Traffic Act",
]


@pytest.mark.parametrize("title", TAX_TITLES)
def test_tax_titles_are_detected(title: str):
    assert is_tax_related(title) is True


@pytest.mark.parametrize("title", NON_TAX_TITLES)
def test_non_tax_titles_are_not_detected(title: str):
    assert is_tax_related(title) is False


def test_is_case_insensitive():
    assert is_tax_related("value added tax act") is True
    assert is_tax_related("CUSTOMS ACT") is True


def test_empty_title_falls_back_to_text():
    assert is_tax_related("", text="This is the Income Tax Act of Estonia.") is True


def test_empty_title_and_text_returns_false():
    assert is_tax_related("") is False
    assert is_tax_related("", text="") is False
    assert is_tax_related("", text="Aliens Act provisions.") is False


def test_word_boundary_avoids_substring_false_positives():
    # "duty" should not match inside an unrelated longer word.
    assert is_tax_related("Dutyfree Imaginary Word Act") is False
