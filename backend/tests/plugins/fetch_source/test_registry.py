"""Tests for fetch_source strategy discovery
(backend.plugins.fetch_source.registry)."""

from __future__ import annotations

import uuid

import pytest

from backend.plugins.fetch_source.base import SourceFetchStrategy
from backend.plugins.fetch_source.registry import (
    build_fetch_strategy,
    get_fetch_strategy_class,
    list_fetch_strategy_configs,
)
from backend.shared.clients.queue.queue_names import (
    FILTER_DOCUMENTS_QUEUE,
    PARSE_SOURCE_QUEUE,
)

_BUILTIN_NAMES = {"web", "local"}


def test_discovers_builtin_strategies():
    names = {cfg.name for cfg in list_fetch_strategy_configs()}
    assert _BUILTIN_NAMES <= names


def test_configs_sorted_by_name():
    names = [cfg.name for cfg in list_fetch_strategy_configs()]
    assert names == sorted(names)


def test_unknown_name_raises_value_error():
    with pytest.raises(ValueError):
        get_fetch_strategy_class("does_not_exist")


@pytest.mark.parametrize("name", sorted(_BUILTIN_NAMES))
def test_build_returns_strategy_instance(name: str):
    strategy = build_fetch_strategy(name)
    assert isinstance(strategy, SourceFetchStrategy)
    assert strategy.config.name == name


@pytest.mark.parametrize(
    ("name", "queue", "dedup_prefix"),
    [
        ("web", PARSE_SOURCE_QUEUE, "parse"),
        ("local", FILTER_DOCUMENTS_QUEUE, "filter"),
    ],
)
def test_strategies_route_to_their_next_stage(name: str, queue: str, dedup_prefix: str):
    target_id = uuid.uuid4()
    event = build_fetch_strategy(name).next_outbox_event(
        target_id=target_id, pipeline_id=None
    )
    assert event.queue_name == queue
    assert event.dedup_key == f"{dedup_prefix}:{target_id}"
    assert event.payload["crawl_target_id"] == str(target_id)
