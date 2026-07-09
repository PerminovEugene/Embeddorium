"""Tests for validate_source strategy discovery
(backend.plugins.validate_source.registry)."""

from __future__ import annotations

import pytest

from backend.plugins.validate_source.base import SourceValidationStrategy
from backend.plugins.validate_source.registry import (
    build_validation_strategy,
    get_validation_strategy_class,
    list_validation_strategy_configs,
)

_BUILTIN_NAMES = {"web", "local"}


def test_discovers_builtin_strategies():
    names = {cfg.name for cfg in list_validation_strategy_configs()}
    assert _BUILTIN_NAMES <= names


def test_configs_sorted_by_name():
    names = [cfg.name for cfg in list_validation_strategy_configs()]
    assert names == sorted(names)


def test_unknown_name_raises_value_error():
    with pytest.raises(ValueError):
        get_validation_strategy_class("does_not_exist")


@pytest.mark.parametrize("name", sorted(_BUILTIN_NAMES))
def test_build_returns_strategy_instance(name: str):
    strategy = build_validation_strategy(name)
    assert isinstance(strategy, SourceValidationStrategy)
    assert strategy.config.name == name
