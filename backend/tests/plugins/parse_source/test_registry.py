"""Tests for parse_source strategy discovery
(backend.plugins.parse_source.registry)."""

from __future__ import annotations

import pytest

from backend.plugins.parse_source.registry import (
    DEFAULT_PARSE_STRATEGY,
    build_parse_strategy,
    get_parse_strategy_class,
    list_parse_strategy_configs,
)

_BUILTIN_NAMES = {"content_type"}


def test_discovers_builtin_strategies():
    names = {cfg.name for cfg in list_parse_strategy_configs()}
    assert _BUILTIN_NAMES <= names


def test_configs_sorted_by_name():
    names = [cfg.name for cfg in list_parse_strategy_configs()]
    assert names == sorted(names)


def test_default_strategy_is_discoverable():
    assert DEFAULT_PARSE_STRATEGY in {cfg.name for cfg in list_parse_strategy_configs()}


def test_configs_expose_populated_fields():
    cfg = get_parse_strategy_class(DEFAULT_PARSE_STRATEGY).config
    assert [f.key for f in cfg.fields] == ["parser"]
    assert cfg.fields[0].type == "select"
    assert cfg.fields[0].default == "auto"


def test_unknown_name_raises_value_error():
    with pytest.raises(ValueError):
        get_parse_strategy_class("does_not_exist")


def test_settings_resolution_falls_back_to_defaults():
    strategy = build_parse_strategy(DEFAULT_PARSE_STRATEGY, {})
    assert strategy._get("parser") == "auto"


def test_unresolvable_content_type_returns_none():
    strategy = build_parse_strategy(DEFAULT_PARSE_STRATEGY, {"parser": "auto"})
    assert strategy.parse(raw="x", content_type="application/zip", final_url="") is None


def test_content_type_selects_parser_and_parses():
    strategy = build_parse_strategy(DEFAULT_PARSE_STRATEGY, {"parser": "auto"})
    out = strategy.parse(raw="hello", content_type="text/plain", final_url="")
    assert isinstance(out, str)


def test_explicit_override_wins_over_content_type():
    strategy = build_parse_strategy(DEFAULT_PARSE_STRATEGY, {"parser": "plain"})
    out = strategy.parse(raw="hello", content_type="application/zip", final_url="")
    assert isinstance(out, str)
