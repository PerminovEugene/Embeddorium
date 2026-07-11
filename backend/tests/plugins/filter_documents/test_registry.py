"""Tests for filter_documents strategy discovery
(backend.plugins.filter_documents.registry)."""

from __future__ import annotations

import pytest

from backend.plugins.filter_documents.registry import (
    DEFAULT_FILTER_STRATEGY,
    build_filter_strategy,
    get_filter_strategy_class,
    list_filter_strategy_configs,
)

_BUILTIN_NAMES = {"keyword"}


def test_discovers_builtin_strategies():
    names = {cfg.name for cfg in list_filter_strategy_configs()}
    assert _BUILTIN_NAMES <= names


def test_configs_sorted_by_name():
    names = [cfg.name for cfg in list_filter_strategy_configs()]
    assert names == sorted(names)


def test_configs_expose_populated_fields():
    cfg = get_filter_strategy_class(DEFAULT_FILTER_STRATEGY).config
    assert [f.key for f in cfg.fields] == ["enabled", "keywords"]


def test_unknown_name_raises_value_error():
    with pytest.raises(ValueError):
        get_filter_strategy_class("does_not_exist")


def test_disabled_gate_passes_everything():
    strategy = build_filter_strategy(
        DEFAULT_FILTER_STRATEGY, {"enabled": False, "keywords": "income"}
    )
    assert strategy.is_relevant(title="Nothing relevant", text="body") is True


def test_empty_keywords_pass_everything():
    strategy = build_filter_strategy(
        DEFAULT_FILTER_STRATEGY, {"enabled": True, "keywords": ""}
    )
    assert strategy.is_relevant(title="Nothing relevant", text="body") is True


def test_keyword_match_gates_relevance():
    strategy = build_filter_strategy(
        DEFAULT_FILTER_STRATEGY, {"enabled": True, "keywords": "income,tax"}
    )
    assert strategy.is_relevant(title="Income Regulations", text="body") is True
    assert strategy.is_relevant(title="General Provisions", text="body") is False
