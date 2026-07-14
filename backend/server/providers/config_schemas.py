"""camelCase API schema for the ``/provider-configs`` endpoint.

Exposes every discovered provider-type adapter's static metadata so the UI can
render a provider-type ``<select>`` and the selected type's settings form
entirely from the backend — the same contract ``/actor-configs`` serves for
strategy plugins, plus two provider-specific fields: ``type`` (in-process
``builtin`` vs. networked ``remote``) and ``supportedModelTypes`` (to constrain
the model-type select).

As with every plugin config, object keys are camelCased on the wire, but a
:class:`~backend.plugins._fields.FieldSpec`'s ``key`` *value* (``model_name``,
``url``, ``mock_dim``, ...) stays snake_case so it round-trips verbatim into the
provider's ``config`` blob.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from backend.plugins._fields import FieldSpec
from backend.plugins.provider_types.base import ProviderTypeConfig


class _CamelModel(BaseModel):
    """Base for API schemas: camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FieldSpecOut(_CamelModel):
    """One UI-configurable setting exposed by a provider-type adapter."""

    key: str
    label: str
    type: str
    default: Any
    min: int | None = None
    max: int | None = None
    options: list[dict[str, Any]] | None = None
    placeholder: str | None = None
    required: bool = False


class ProviderTypeConfigOut(_CamelModel):
    """One discovered provider-type adapter's static, UI-facing metadata."""

    name: str
    label: str
    description: str
    type: str
    supported_model_types: list[str] = Field(default_factory=list)
    fields: list[FieldSpecOut] = Field(default_factory=list)


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


def provider_type_config_to_out(config: ProviderTypeConfig) -> ProviderTypeConfigOut:
    """Map a provider-type adapter's static config to its response schema."""
    return ProviderTypeConfigOut(
        name=config.name,
        label=config.label,
        description=config.description,
        type=config.type,
        supported_model_types=list(config.supported_model_types),
        fields=[_field_to_out(f) for f in config.fields],
    )
