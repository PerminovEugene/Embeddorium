"""The provider-type adapter interface.

A provider-type adapter owns the provider-specific half of embedding: turning a
stored :class:`~backend.shared.models.provider.Provider`'s ``config`` blob into
the concrete :class:`ResolvedEmbedTarget` the embed clients need (a worker-facing
provider key, the model to load, an optional endpoint, and the mock dimension).
Everything else — the model cache, the encode loop, vector upsert, HTTP — stays
in the embed clients and the actor/launcher, which are provider-agnostic.

Every adapter declares a class-level :class:`ProviderTypeConfig`, sharing the
same ``name``/``label``/``description``/``fields`` shape as every other plugin
config so one API schema serves them all, plus two provider-specific pieces of
metadata: ``type`` (in-process ``"builtin"`` vs. networked ``"remote"``) and
``supported_model_types`` (the capabilities the UI's model-type select should be
constrained to).

``__init__`` resolves the raw ``config`` dict against ``config.fields``, filling
each field's ``default`` for any missing key — the same settings-resolution
convenience the chunker/embed_chunks plugins offer. Subclasses read values via
:meth:`_get` and implement :meth:`resolve`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

from backend.plugins._fields import FieldSpec
from backend.shared.models.provider import ModelType

# Where an adapter's model actually runs. ``builtin`` = in-process, no network
# (fastembed, mock); ``remote`` = a server/API reached over the network (ollama,
# openai). This is a fixed property of the adapter, not a per-provider user
# choice, so it lives on the config as metadata rather than as a ``FieldSpec``.
ProviderType = Literal["builtin", "remote"]


@dataclass(frozen=True)
class ProviderTypeConfig:
    """Static, UI-facing description of a provider-type adapter.

    ``name`` is the stable id the adapter is looked up under (and the value
    stored in ``Provider.provider_type``). ``type`` and
    ``supported_model_types`` are advertised to the UI so it can group the
    provider-type picker and constrain the model-type select; ``fields``
    describes the settings form and is the single source of truth for what the
    adapter's ``config`` blob may contain.
    """

    name: str
    label: str
    description: str
    type: ProviderType
    supported_model_types: tuple[ModelType, ...]
    fields: list[FieldSpec] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedEmbedTarget:
    """The concrete embedding target derived from a provider's ``config``.

    ``provider`` is the worker-facing embed-client key (``"ollama"`` /
    ``"mock"`` / ``"fastembed"`` / ``"huggingface"``); ``model`` is the model to
    load; ``base_url`` and ``api_key`` are connection settings for networked
    providers (``None`` for in-process ones); ``mock_dim`` is the vector size
    for the mock provider (``None`` for real providers).
    """

    provider: str
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    mock_dim: int | None = None


@dataclass(frozen=True)
class ResolvedRerankTarget:
    """The concrete reranking target derived from a provider's ``config``.

    Reranking is a distinct capability from embedding — a cross-encoder scores
    ``(query, candidate)`` pairs rather than producing a vector — so it resolves
    to its own target dataclass instead of overloading
    :class:`ResolvedEmbedTarget`. ``provider`` is the worker-facing rerank-client
    key (``"http_rerank"``); ``model`` is the reranker model served by that
    endpoint; ``base_url`` and ``api_key`` are the connection settings for the
    remote server (the reranker runs as a networked service — e.g. vLLM /
    Infinity / Cohere — not in-process, so torch/sentence-transformers never
    enter the container path). ``path`` is the rerank endpoint relative to
    ``base_url`` — servers disagree (vLLM ``v1/rerank``, Infinity ``rerank``) so
    it is resolved per-provider rather than hardcoded in the client.
    """

    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    path: str = "v1/rerank"


class ProviderTypeAdapter(ABC):
    """Base class every provider-type adapter subclasses."""

    config: ClassVar[ProviderTypeConfig]

    def __init__(self, values: dict[str, Any] | None = None) -> None:
        values = values or {}
        # Resolve the raw provider config against the declared fields, filling
        # per-field defaults for any missing key. Unknown keys are dropped, so
        # the adapter only ever sees keys it declared.
        self.values = {
            field.key: self._validate_value(
                field,
                values.get(field.key, field.default),
            )
            for field in self.config.fields
        }

    @staticmethod
    def _validate_value(field: FieldSpec, value: Any) -> Any:
        """Validate one JSON value against its UI field descriptor."""
        if value is None:
            if field.required:
                raise ValueError(f"Provider config field {field.key!r} is required")
            return None

        if field.type == "text":
            if not isinstance(value, str):
                raise ValueError(f"Provider config field {field.key!r} must be text")
            if field.required and not value.strip():
                raise ValueError(f"Provider config field {field.key!r} is required")
            return value

        if field.type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    f"Provider config field {field.key!r} must be a number"
                )
            if field.min is not None and value < field.min:
                raise ValueError(
                    f"Provider config field {field.key!r} must be at least {field.min}"
                )
            if field.max is not None and value > field.max:
                raise ValueError(
                    f"Provider config field {field.key!r} must be at most {field.max}"
                )
            return value

        if field.type == "checkbox":
            if not isinstance(value, bool):
                raise ValueError(
                    f"Provider config field {field.key!r} must be a boolean"
                )
            return value

        if field.type == "select":
            allowed = {option.get("value") for option in field.options or []}
            if value not in allowed:
                raise ValueError(
                    f"Provider config field {field.key!r} has unsupported value {value!r}"
                )
            return value

        return value

    def _get(self, key: str) -> Any:
        """Return the resolved value for a declared field key."""
        return self.values[key]

    def resolved_config(self) -> dict[str, Any]:
        """Return the config resolved against the adapter's field defaults."""
        return dict(self.values)

    @abstractmethod
    def resolve(self) -> ResolvedEmbedTarget:
        """Resolve this provider's config into a concrete embed target.

        Adapters whose capability is not embedding (e.g. a cross-encoder
        reranker) must still implement this abstract method, but should raise a
        clear error here so they can never be picked as an embed target, and
        implement :meth:`resolve_rerank` instead.
        """
        raise NotImplementedError

    def resolve_rerank(self) -> ResolvedRerankTarget:
        """Resolve this provider's config into a concrete rerank target.

        The default raises: only reranker adapters (``cross-encoder``) override
        it. This keeps ``resolve``/``resolve_rerank`` symmetric with the two
        capabilities without forcing every embedding adapter to implement a
        method it has no use for.
        """
        raise NotImplementedError(
            f"Provider type {type(self).__name__!r} does not support reranking"
        )
