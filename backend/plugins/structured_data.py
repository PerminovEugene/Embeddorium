"""JSON-safe structured data shared by parser and chunker plugins."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TypeAlias

from pydantic import JsonValue as PydanticJsonValue

JsonValue: TypeAlias = PydanticJsonValue
JsonObject: TypeAlias = dict[str, JsonValue]


class StructuredDataError(ValueError):
    """Raised when plugin data is not JSON compatible or exceeds its limit."""


def validate_json_size(
    value: JsonValue,
    *,
    limit: int,
    kind: str,
    plugin_name: str,
    source: str,
) -> int:
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise StructuredDataError(
            f"{plugin_name} produced non-JSON-compatible {kind} for {source}: {exc}"
        ) from exc
    actual = len(encoded.encode("utf-8"))
    if actual > limit:
        raise StructuredDataError(
            f"{plugin_name} {kind} for {source} exceeds configured limit "
            f"{limit} bytes (actual {actual} bytes)"
        )
    return actual


@dataclass(frozen=True)
class ParsedDocument:
    """Normalized text plus optional opaque, versioned structured output."""

    text: str
    metadata: JsonObject = field(default_factory=dict)
    intermediate: JsonValue = None
    output_format: str | None = None
    parser_name: str | None = None


def normalize_parsed_document(value: str | ParsedDocument) -> ParsedDocument:
    """Adapt legacy text-only parser results to the structured contract."""
    if isinstance(value, ParsedDocument):
        return ParsedDocument(
            text=value.text,
            metadata=dict(value.metadata),
            intermediate=value.intermediate,
            output_format=value.output_format,
            parser_name=value.parser_name,
        )
    return ParsedDocument(text=value)
