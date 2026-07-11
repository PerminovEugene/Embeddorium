"""camelCase API schema for the ``/actor-configs`` endpoint.

Exposes, for every plugin-backed actor, the statically-declared strategy
configs discovered under ``backend/plugins/<actor>`` so the UI can render a
strategy picker plus each strategy's own settings form — the same contract
already served per-chunker by ``/chunkers``, generalised to every actor.

Every strategy config (``FetchStrategyConfig``, ``ParseStrategyConfig``,
``ChunkerConfig``, ...) shares the same shape — ``name``/``label``/
``description`` plus a ``fields: list[FieldSpec]`` — so one response schema
serves them all. ``restrictions`` is optional (only chunker configs carry it).

Every JSON *object key* is camelCased like the rest of the API layer, but a
:class:`~backend.plugins._fields.FieldSpec`'s ``key`` *value* (e.g.
``"chunk_size"``, ``"verify_tls"``) is left untouched: it is the exact
snake_case key the UI must send back inside the actor's settings block, so
transforming it would break the round trip.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, Sequence

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from backend.plugins._fields import FieldSpec


class _StrategyConfigLike(Protocol):
    """Structural type for any plugin's static strategy config.

    Every ``*StrategyConfig``/``ChunkerConfig`` dataclass satisfies this;
    ``restrictions`` is only present on chunker configs (read defensively).
    """

    name: str
    label: str
    description: str
    fields: Sequence[FieldSpec]


class _CamelModel(BaseModel):
    """Base for API schemas: camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FieldSpecOut(_CamelModel):
    """One UI-configurable setting exposed by a strategy plugin."""

    key: str
    label: str
    type: str
    default: Any
    min: Optional[int] = None
    max: Optional[int] = None
    options: Optional[List[Dict[str, Any]]] = None
    placeholder: Optional[str] = None
    required: bool = False


class StrategyConfigOut(_CamelModel):
    """One discovered strategy plugin's static, UI-facing metadata."""

    name: str
    label: str
    description: str
    restrictions: str = ""
    fields: List[FieldSpecOut] = []


class ActorConfigOut(_CamelModel):
    """Every strategy available for one plugin-backed actor."""

    actor: str
    strategies: List[StrategyConfigOut] = []


def _field_to_out(field: FieldSpec) -> FieldSpecOut:
    return FieldSpecOut(
        key=field.key,
        label=field.label,
        type=field.type,
        default=field.default,
        min=field.min,
        max=field.max,
        options=field.options,
        placeholder=field.placeholder,
        required=field.required,
    )


def strategy_config_to_out(config: _StrategyConfigLike) -> StrategyConfigOut:
    """Map any plugin strategy config to its camelCase response schema."""
    return StrategyConfigOut(
        name=config.name,
        label=config.label,
        description=config.description,
        restrictions=getattr(config, "restrictions", "") or "",
        fields=[_field_to_out(f) for f in config.fields],
    )
