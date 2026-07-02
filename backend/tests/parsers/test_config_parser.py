import json
from pathlib import Path

import pytest

from backend.shared.parsers.config_parser import parse_sources_config


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(data))
    return path


def test_web_source_defaults_type_to_web(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "sources": [
                    {"description": "Tax authority", "link": "https://emta.ee"},
                ],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    config = parse_sources_config(path)

    source = config.groups[0].sources[0]
    assert source.type == "web"
    assert source.link == "https://emta.ee"
    assert source.path is None


def test_explicit_web_type_is_accepted(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "sources": [
                    {
                        "description": "Tax authority",
                        "link": "https://emta.ee",
                        "type": "web",
                    },
                ],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    config = parse_sources_config(path)

    assert config.groups[0].sources[0].type == "web"


def test_xml_source_parses_path_and_glob(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "sources": [
                    {
                        "description": "Sample XML dump.",
                        "type": "xml",
                        "path": "xml.2026.en",
                        "glob": "*.xml",
                    },
                ],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    config = parse_sources_config(path)

    source = config.groups[0].sources[0]
    assert source.type == "xml"
    assert source.path == "xml.2026.en"
    assert source.glob == "*.xml"


def test_xml_source_glob_defaults_to_xml_pattern(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "sources": [
                    {
                        "description": "Sample XML dump.",
                        "type": "xml",
                        "path": "xml.2026.en",
                    },
                ],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    config = parse_sources_config(path)

    assert config.groups[0].sources[0].glob == "*.xml"


def test_xml_source_without_path_raises(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "sources": [
                    {"description": "Missing path.", "type": "xml"},
                ],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    with pytest.raises(ValueError):
        parse_sources_config(path)


def test_unknown_source_type_raises(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "sources": [
                    {
                        "description": "Bad type.",
                        "type": "ftp",
                        "link": "https://emta.ee",
                    },
                ],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    with pytest.raises(ValueError):
        parse_sources_config(path)


def test_web_source_without_link_raises(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "sources": [
                    {"description": "Missing link."},
                ],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    with pytest.raises(ValueError):
        parse_sources_config(path)


def test_backward_compatible_config_without_type_field(tmp_path: Path):
    """Existing config.json files (no 'type' anywhere) keep working."""
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "sources": [
                    {"description": "Tax authority", "link": "emta.ee"},
                    {"description": "Laws", "link": "https://example.com"},
                ],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    config = parse_sources_config(path)

    assert len(config.groups[0].sources) == 2
    assert all(s.type == "web" for s in config.groups[0].sources)


def test_group_without_settings_has_none(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "sources": [{"description": "Tax authority", "link": "emta.ee"}],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    config = parse_sources_config(path)

    assert config.groups[0].settings is None


def test_group_settings_are_parsed_per_actor(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "settings": {
                    "chunk_document": {
                        "strategy": "markdown",
                        "chunk_size": 800,
                        "chunk_overlap": 80,
                    },
                    "embed_chunks": {
                        "provider": "ollama",
                        "model": "qwen3-embedding",
                        "mock_dim": None,
                    },
                    "vector_store": {"similarity": "dot"},
                },
                "sources": [{"description": "Tax authority", "link": "emta.ee"}],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    settings = parse_sources_config(path).groups[0].settings

    assert settings is not None
    assert settings.chunk_document.chunk_size == 800
    assert settings.chunk_document.chunk_overlap == 80
    assert settings.embed_chunks.provider == "ollama"
    assert settings.embed_chunks.model == "qwen3-embedding"
    assert settings.vector_store.similarity == "dot"


def test_partial_group_settings_leave_omitted_actors_none(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "settings": {"embed_chunks": {"provider": "mock", "mock_dim": 64}},
                "sources": [{"description": "Tax authority", "link": "emta.ee"}],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    settings = parse_sources_config(path).groups[0].settings

    assert settings.chunk_document is None
    assert settings.vector_store is None
    assert settings.embed_chunks.provider == "mock"
    assert settings.embed_chunks.mock_dim == 64


def test_non_integer_chunk_size_is_rejected(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "example",
                "attributes": {"code": "EE"},
                "settings": {"chunk_document": {"chunk_size": "big"}},
                "sources": [{"description": "Tax authority", "link": "emta.ee"}],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    with pytest.raises(ValueError, match="chunk_size"):
        parse_sources_config(path)
