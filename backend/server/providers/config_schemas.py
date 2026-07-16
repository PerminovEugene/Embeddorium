"""camelCase API schema for the ``/provider-configs`` endpoint.

Exposes every discovered provider type's static metadata so the UI can render a
provider-type ``<select>``, then a model-type ``<select>`` constrained to what
that provider serves, then the fields for the chosen combination — entirely from
the backend. The same contract ``/actor-configs`` serves for strategy plugins,
plus two provider-specific pieces: ``type`` (in-process ``builtin`` vs. networked
``remote``) and a ``modelTypes`` list carrying each supported capability with its
own capability-specific ``fields`` (``supportedModelTypes`` is the flat view of
their ids, kept for the model-type ``<select>``).

Fields are split across two levels: the provider's ``fields`` are the shared
connection settings (``url``/``port``/``api_key``); each model type's ``fields``
are its capability settings (``model_name``, ``mock_dim``, ``rerank_path``). The
UI renders the union of the provider's connection fields and the selected model
type's fields into one form, which round-trips back into the provider's flat
``config`` blob.

As with every plugin config, object keys are camelCased on the wire, but a
:class:`~backend.plugins._fields.FieldSpec`'s ``key`` *value* (``model_name``,
``url``, ``mock_dim``, ...) stays snake_case so it round-trips verbatim.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from backend.plugins._fields import FieldSpec
from backend.plugins.provider_types.registry import ProviderTypeView


class _CamelModel(BaseModel):
    """Base for API schemas: camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FieldSpecOut(_CamelModel):
    """One UI-configurable setting exposed by a provider or model type."""

    key: str
    label: str
    type: str
    default: Any
    min: int | None = None
    max: int | None = None
    options: list[dict[str, Any]] | None = None
    placeholder: str | None = None
    required: bool = False


class ModelTypeConfigOut(_CamelModel):
    """One model type a provider serves, with its capability-specific fields."""

    model_type: str
    label: str
    fields: list[FieldSpecOut] = Field(default_factory=list)


class ProviderTypeConfigOut(_CamelModel):
    """One discovered provider type's static, UI-facing metadata."""

    name: str
    label: str
    description: str
    type: str
    supported_model_types: list[str] = Field(default_factory=list)
    fields: list[FieldSpecOut] = Field(default_factory=list)
    model_types: list[ModelTypeConfigOut] = Field(default_factory=list)


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


def provider_type_config_to_out(config: ProviderTypeView) -> ProviderTypeConfigOut:
    """Map a provider type's discovered view to its response schema."""
    return ProviderTypeConfigOut(
        name=config.name,
        label=config.label,
        description=config.description,
        type=config.type,
        supported_model_types=list(config.supported_model_types),
        fields=[_field_to_out(f) for f in config.fields],
        model_types=[
            ModelTypeConfigOut(
                model_type=mt.model_type,
                label=mt.label,
                fields=[_field_to_out(f) for f in mt.fields],
            )
            for mt in config.model_types
        ],
    )
