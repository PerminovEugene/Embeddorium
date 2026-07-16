"""The provider-type / model-type adapter interfaces.

Embedding (and reranking) is described by two layers, mirroring how a real
deployment is configured:

- A **provider type** is the runtime/API you talk to — ``mock``, ``ollama``,
  ``openai``. It owns the *connection*: the ``url``/``port``/``api_key`` shared by
  every model that provider serves, plus the ``type`` metadata (in-process
  ``"builtin"`` vs. networked ``"remote"``). A provider type is a
  :class:`ProviderTypeAdapter` with a class-level :class:`ProviderTypeConfig`.
- A **model type** is the capability a model serves under a provider —
  ``embedding``, ``cross-encoder`` (reranker), … . It owns the
  *capability-specific* settings (``model_name``, ``mock_dim``, ``rerank_path``)
  and the code that turns them, plus the provider's resolved connection, into a
  concrete target (:class:`ResolvedEmbedTarget` / :class:`ResolvedRerankTarget`)
  and, for embedding, an :class:`~backend.shared.clients.embed_client.EmbedClient`.
  A model type is a :class:`ModelTypeHandler` with a class-level
  :class:`ModelTypeConfig`, discovered from the provider's ``model_types/``
  subpackage.

A cross-encoder reranker is therefore a *model type* offered under a provider
(``ollama``), not a provider type of its own.

The persisted :class:`~backend.shared.models.provider.Provider` stays a flat
``{provider_type, model_type, config}`` record. When resolving, the single
``config`` blob is validated against the *union* of the provider's connection
fields and the selected model-type handler's fields — the provider adapter reads
the connection keys, the handler reads the capability keys, each ignoring keys it
did not declare.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from backend.plugins._fields import FieldSpec

if TYPE_CHECKING:
    from backend.shared.clients.embed_client import EmbedClient

# Where a provider's model actually runs. ``builtin`` = in-process, no network
# (mock); ``remote`` = a server/API reached over the network (ollama, openai).
# This is a fixed property of the provider type, not a per-provider user choice,
# so it lives on the config as metadata rather than as a ``FieldSpec``.
ProviderType = Literal["builtin", "remote"]


@dataclass(frozen=True)
class ProviderTypeConfig:
    """Static, UI-facing description of a provider type.

    ``name`` is the stable id the provider is looked up under (and the value
    stored in ``Provider.provider_type``). ``type`` is advertised to the UI so it
    can group the provider-type picker; ``fields`` describes the provider's
    *connection* form (url/port/api_key) — the capability-specific fields live on
    each :class:`ModelTypeConfig` instead.
    """

    name: str
    label: str
    description: str
    type: ProviderType
    fields: list[FieldSpec] = field(default_factory=list)


@dataclass(frozen=True)
class ModelTypeConfig:
    """Static, UI-facing description of one model type served by a provider.

    ``model_type`` is the capability id (``embedding``, ``cross-encoder``, …) —
    the value stored in ``Provider.model_type`` — and ``fields`` describes the
    capability-specific settings form (``model_name``, ``mock_dim``,
    ``rerank_path``) rendered under the provider's connection form.
    """

    model_type: str
    label: str
    fields: list[FieldSpec] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedConnection:
    """The provider's resolved connection, handed to its model-type handlers.

    ``base_url`` and ``api_key`` are the networked-provider settings (both
    ``None`` for the in-process mock). A model-type handler combines these with
    its own ``model_name`` to build a concrete target/client.
    """

    base_url: str | None = None
    api_key: str | None = None


@dataclass(frozen=True)
class ResolvedEmbedTarget:
    """The concrete embedding target derived from a provider's ``config``.

    ``provider`` is the worker-facing embed-client key (``"ollama"`` /
    ``"openai"`` / ``"mock"``); ``model`` is the model to load; ``base_url`` and
    ``api_key`` are connection settings for networked providers (``None`` for
    in-process ones); ``mock_dim`` is the vector size for the mock provider
    (``None`` for real providers).
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
    it is resolved per-model-type rather than hardcoded in the client.
    """

    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    path: str = "v1/rerank"


def _validate_value(field: FieldSpec, value: Any) -> Any:
    """Validate one JSON value against its UI field descriptor.

    Shared by both :class:`ProviderTypeAdapter` and :class:`ModelTypeHandler`:
    the two layers split a provider's flat ``config`` between them but validate
    their own keys the same way.
    """
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
            raise ValueError(f"Provider config field {field.key!r} must be a number")
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
            raise ValueError(f"Provider config field {field.key!r} must be a boolean")
        return value

    if field.type == "select":
        allowed = {option.get("value") for option in field.options or []}
        if value not in allowed:
            raise ValueError(
                f"Provider config field {field.key!r} has unsupported value {value!r}"
            )
        return value

    return value


def _resolve_config(fields: list[FieldSpec], values: dict[str, Any] | None) -> dict:
    """Resolve *values* against *fields*, filling per-field defaults.

    Fills each declared field's ``default`` for any missing key and drops keys
    not declared here, so a layer only ever sees the keys it owns.
    """
    values = values or {}
    return {
        field.key: _validate_value(field, values.get(field.key, field.default))
        for field in fields
    }


class ProviderTypeAdapter(ABC):
    """Base class every provider type subclasses.

    Owns the provider's *connection*: it resolves the ``config`` blob against its
    connection ``fields`` and exposes :meth:`resolve_connection`, whose
    :class:`ResolvedConnection` is handed to the selected model-type handler.
    """

    config: ClassVar[ProviderTypeConfig]

    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self.values = _resolve_config(self.config.fields, values)

    def _get(self, key: str) -> Any:
        """Return the resolved value for a declared connection field key."""
        return self.values[key]

    def resolved_config(self) -> dict[str, Any]:
        """Return the connection config resolved against its field defaults."""
        return dict(self.values)

    @abstractmethod
    def resolve_connection(self) -> ResolvedConnection:
        """Resolve this provider's connection settings.

        Networked providers assemble a ``base_url`` (and optionally an
        ``api_key``); the in-process mock returns an empty connection.
        """
        raise NotImplementedError


class ModelTypeHandler(ABC):
    """Base class every model-type handler subclasses.

    A handler serves one capability (``config.model_type``) under a provider. It
    resolves its capability-specific ``config`` keys and combines them with the
    provider's :class:`ResolvedConnection` to build a concrete target/client.

    :meth:`resolve` + :meth:`build_embed_client` are for embedding handlers;
    :meth:`resolve_rerank` is for reranker handlers. The defaults raise so a
    handler that serves one capability can never be driven as the other.
    """

    config: ClassVar[ModelTypeConfig]

    def __init__(
        self,
        values: dict[str, Any] | None = None,
        connection: ResolvedConnection | None = None,
    ) -> None:
        self.values = _resolve_config(self.config.fields, values)
        self.connection = connection or ResolvedConnection()

    def _get(self, key: str) -> Any:
        """Return the resolved value for a declared capability field key."""
        return self.values[key]

    def resolved_config(self) -> dict[str, Any]:
        """Return the capability config resolved against its field defaults."""
        return dict(self.values)

    def resolve(self) -> ResolvedEmbedTarget:
        """Resolve this model type's config into a concrete embed target."""
        raise NotImplementedError(
            f"Model type {self.config.model_type!r} does not support embedding"
        )

    def build_embed_client(self) -> EmbedClient:
        """Build the embed client this model type embeds with.

        The provider-specific *strategy* the embed actor (and compare/search)
        dispatch through instead of a hardcoded ``if provider == ...`` switch:
        each embedding handler owns how to construct its client — importing its
        heavy backend lazily, reusing :meth:`resolve` for model/endpoint
        resolution — so callers only ``build_embed_client()`` and ``encode``.
        """
        raise NotImplementedError(
            f"Model type {self.config.model_type!r} does not support embedding"
        )

    def resolve_rerank(self) -> ResolvedRerankTarget:
        """Resolve this model type's config into a concrete rerank target."""
        raise NotImplementedError(
            f"Model type {self.config.model_type!r} does not support reranking"
        )
