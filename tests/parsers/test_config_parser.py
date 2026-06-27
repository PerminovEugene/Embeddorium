import json
from pathlib import Path

import pytest

from laws_agent.parsers.config_parser import parse_sources_config


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(data))
    return path


def test_web_source_defaults_type_to_web(tmp_path: Path):
    data = {
        "groups": [
            {
                "name": "Estonia",
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
                "name": "Estonia",
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
                "name": "Estonia",
                "attributes": {"code": "EE"},
                "sources": [
                    {
                        "description": "Estonian acts XML dump.",
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
                "name": "Estonia",
                "attributes": {"code": "EE"},
                "sources": [
                    {
                        "description": "Estonian acts XML dump.",
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
                "name": "Estonia",
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
                "name": "Estonia",
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
                "name": "Estonia",
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
                "name": "Estonia",
                "attributes": {"code": "EE"},
                "sources": [
                    {"description": "Tax authority", "link": "emta.ee"},
                    {"description": "Laws", "link": "https://riigiteataja.ee"},
                ],
            }
        ]
    }
    path = _write_config(tmp_path, data)

    config = parse_sources_config(path)

    assert len(config.groups[0].sources) == 2
    assert all(s.type == "web" for s in config.groups[0].sources)
