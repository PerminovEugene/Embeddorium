"""camelCase API schema for the ``/chunkers`` endpoint.

Exposes the statically-declared ``ChunkerConfig`` metadata for every
discovered chunker plugin (``backend/plugins/chunkers``) so the UI can
render a chunker picker plus each chunker's own settings form. Pure
read-only mapping — no domain writes happen through this endpoint.

Every JSON *object key* is camelCased like the rest of the API layer, but
``ChunkerFieldOut.key``'s *value* (e.g. ``"chunk_size"``) is left untouched:
it is the exact snake_case key the UI must send back inside
``ChunkDocumentSettings.settings`` (see
``backend.shared.models.pipeline_run.ChunkDocumentSettings``), so
transforming it would break the round trip.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from backend.plugins.chunkers.base import ChunkerConfig


class _CamelModel(BaseModel):
    """Base for API schemas: camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ChunkerFieldOut(_CamelModel):
    """One UI-configurable setting of a chunker plugin."""

    key: str
    label: str
    type: str
    default: Any
    min: Optional[int] = None
    max: Optional[int] = None
    options: Optional[List[Dict[str, Any]]] = None
    placeholder: Optional[str] = None


class ChunkerConfigOut(_CamelModel):
    """A discovered chunker plugin's static, UI-facing metadata."""

    name: str
    label: str
    description: str
    restrictions: str = ""
    fields: List[ChunkerFieldOut] = []


def chunker_config_to_out(config: ChunkerConfig) -> ChunkerConfigOut:
    """Map a domain ``ChunkerConfig`` to its camelCase response schema."""
    return ChunkerConfigOut(
        name=config.name,
        label=config.label,
        description=config.description,
        restrictions=config.restrictions,
        fields=[
            ChunkerFieldOut(
                key=f.key,
                label=f.label,
                type=f.type,
                default=f.default,
                min=f.min,
                max=f.max,
                options=f.options,
                placeholder=f.placeholder,
            )
            for f in config.fields
        ],
    )
