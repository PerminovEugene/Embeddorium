"""Semantics of the ``keyword`` filter strategy (include + exclude gates)."""

from __future__ import annotations

from backend.plugins.filter_documents.keyword import KeywordFilter


def _filter(**settings) -> KeywordFilter:
    return KeywordFilter({"enabled": True, **settings})


def test_disabled_gate_passes_everything_regardless_of_lists():
    strategy = KeywordFilter(
        {"enabled": False, "keywords": "income", "exclude_keywords": "income"}
    )
    assert strategy.is_relevant(title="Income repealed", text="body") is True


def test_empty_lists_pass_everything():
    strategy = _filter(keywords="", exclude_keywords="")
    assert strategy.is_relevant(title="Anything", text="body") is True


def test_include_only_gates_on_match():
    strategy = _filter(keywords="income,tax")
    assert strategy.is_relevant(title="Income Regulations", text="body") is True
    assert strategy.is_relevant(title="General Provisions", text="body") is False


def test_exclude_only_drops_on_match_and_keeps_otherwise():
    strategy = _filter(exclude_keywords="draft,repealed")
    # No include list → everything not excluded passes.
    assert strategy.is_relevant(title="Income Act", text="body") is True
    assert strategy.is_relevant(title="Draft Income Act", text="body") is False


def test_exclude_wins_over_include():
    strategy = _filter(keywords="income", exclude_keywords="draft")
    # Matches the include list but also the exclude list → dropped.
    assert strategy.is_relevant(title="Draft income act", text="body") is False
    # Matches include and not exclude → kept.
    assert strategy.is_relevant(title="Income act", text="body") is True


def test_exclude_matches_body_when_title_empty_web_like():
    # Web/HTML content: extract_act_title returns "" so the title is empty and
    # both gates fall back to the raw body.
    strategy = _filter(exclude_keywords="repealed")
    body = "<html><body>This regulation has been repealed.</body></html>"
    assert strategy.is_relevant(title="", text=body) is False
    assert strategy.is_relevant(title=None, text="<html>active law</html>") is True


def test_include_matches_body_when_title_empty_web_like():
    strategy = _filter(keywords="income")
    assert strategy.is_relevant(title="", text="income tax rules") is True
    assert strategy.is_relevant(title="", text="unrelated content") is False


def test_exclude_matches_body_even_when_title_present():
    # matches_any consults title AND body (unlike the include fallback), so an
    # exclude keyword in the body drops a doc whose title matched include.
    strategy = _filter(keywords="income", exclude_keywords="repealed")
    assert (
        strategy.is_relevant(title="Income Act", text="this act is repealed") is False
    )
