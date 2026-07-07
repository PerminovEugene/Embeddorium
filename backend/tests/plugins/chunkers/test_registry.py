"""Tests for chunker plugin discovery (backend.plugins.chunkers.registry)."""

from __future__ import annotations

import pytest

from backend.plugins.chunkers.registry import (
    DEFAULT_CHUNKER,
    build_chunker,
    get_chunker_class,
    list_chunker_configs,
)

_BUILTIN_NAMES = {
    "text_markdown",
    "text_section",
    "text_recursive",
    "text_fixed",
    "text_sentence",
    "text_sliding_window",
    "legal_xml",
}


def test_discovers_all_builtin_chunkers():
    names = {cfg.name for cfg in list_chunker_configs()}
    assert _BUILTIN_NAMES <= names


def test_list_chunker_configs_sorted_by_name():
    names = [cfg.name for cfg in list_chunker_configs()]
    assert names == sorted(names)


def test_default_chunker_is_registered():
    assert DEFAULT_CHUNKER in {cfg.name for cfg in list_chunker_configs()}


def test_get_chunker_class_unknown_name_raises_value_error():
    with pytest.raises(ValueError):
        get_chunker_class("does_not_exist")


def test_build_chunker_returns_configured_instance():
    chunker = build_chunker("text_markdown", {"chunk_size": 50, "chunk_overlap": 5})
    assert chunker.settings["chunk_size"] == 50
    assert chunker.settings["chunk_overlap"] == 5


def test_build_chunker_fills_defaults_for_missing_settings():
    chunker = build_chunker("text_markdown", {})
    assert chunker.settings["chunk_size"] == 1200
    assert chunker.settings["chunk_overlap"] == 150


def test_text_section_has_no_size_fields():
    cfg = get_chunker_class("text_section").config
    assert cfg.fields == []


def test_legal_xml_has_restrictions_note():
    cfg = get_chunker_class("legal_xml").config
    assert "XML" in cfg.restrictions
