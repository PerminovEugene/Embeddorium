from __future__ import annotations

import pytest

from backend.actors.chunk_document_actor.handler import _merged_metadata
from backend.plugins.chunkers.base import (
    Chunk,
    ChunkerConfig,
    validate_parser_chunker_compatibility,
)
from backend.plugins.structured_data import (
    ParsedDocument,
    StructuredDataError,
    normalize_parsed_document,
    validate_json_size,
)
from backend.shared.models import Document


def test_legacy_parser_text_is_adapted() -> None:
    assert normalize_parsed_document("plain") == ParsedDocument(text="plain")


def test_structured_parser_result_is_preserved() -> None:
    result = normalize_parsed_document(
        ParsedDocument(
            text="act",
            metadata={"nested": {"values": [1, True, None]}},
            intermediate={"nodes": [{"id": "p1"}]},
            output_format="legal-ir/v1",
        )
    )
    assert result.intermediate == {"nodes": [{"id": "p1"}]}


def test_parser_chunker_format_compatibility() -> None:
    config = ChunkerConfig(
        name="structured",
        label="Structured",
        description="",
        accepted_input_formats=("legal-ir/v1",),
    )
    validate_parser_chunker_compatibility("legal-ir/v1", config)
    with pytest.raises(ValueError, match="expects parser output"):
        validate_parser_chunker_compatibility("other/v1", config)


def test_metadata_inheritance_and_chunk_precedence() -> None:
    document = Document(
        id="53b76aa9-b5bb-44bf-98e8-540fa417c914",
        source_url="https://example.test/act",
        parser_metadata={"jurisdiction": "EE", "title": "Old"},
    )
    merged = _merged_metadata(
        document=document,
        chunk=Chunk(text="body", metadata={"title": "Current", "node": {"id": 1}}),
        chunker_name="structured",
    )
    assert merged == {"jurisdiction": "EE", "title": "Current", "node": {"id": 1}}


def test_reserved_metadata_is_rejected() -> None:
    document = Document(
        id="53b76aa9-b5bb-44bf-98e8-540fa417c914", source_url="https://example.test/act"
    )
    with pytest.raises(ValueError, match="reserved keys"):
        _merged_metadata(
            document=document,
            chunk=Chunk(text="body", metadata={"document_id": "fake"}),
            chunker_name="structured",
        )


def test_oversized_metadata_has_actionable_error() -> None:
    with pytest.raises(StructuredDataError, match=r"limit 10 bytes \(actual"):
        validate_json_size(
            {"value": "too large"},
            limit=10,
            kind="metadata",
            plugin_name="xml",
            source="document.xml",
        )
