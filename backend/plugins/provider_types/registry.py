"""Discovery/lookup for the two-level provider-type / model-type structure.

Each provider type is a folder under ``backend/plugins/provider_types/<name>/``:
its :class:`ProviderTypeAdapter` lives in ``base.py`` and its
:class:`ModelTypeHandler` capabilities live in ``model_types/*.py``. Discovery
walks the whole package once per process (cached at module level), collects every
concrete adapter and handler, and associates each handler with the provider whose
package contains it — so a provider's ``supported_model_types`` is *derived* from
the handlers it actually ships, never hardcoded.

On top of the ``list``/``get``/``build`` trio this module exposes the helpers the
rest of the app dispatches through instead of hardcoding provider branches. They
now all take the selected ``model_type`` too, because resolution is per model
type: the provider supplies the connection, the model-type handler supplies the
model/capability.

- :func:`validate_provider` — validate a provider's ``(provider_type,
  model_type, config)`` and return the resolved (connection + capability) blob.
- :func:`resolve_embed_target` / :func:`build_embed_client` — turn a
  ``(provider_type, model_type, config)`` triple into a concrete embed
  target/client.
- :func:`resolve_rerank_target` — the rerank equivalent.

An unknown ``provider_type`` (or a ``model_type`` the provider does not serve)
raises ``ValueError``: Embeddorium only talks to remote (ollama/openai) and mock
providers, so there is no in-process fallback to silently degrade to.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from backend.plugins._fields import FieldSpec
from backend.plugins.provider_types.base import (
    ModelTypeHandler,
    ProviderType,
    ProviderTypeAdapter,
    ResolvedEmbedTarget,
    ResolvedRerankTarget,
)

if TYPE_CHECKING:
    from backend.shared.clients.embed_client import EmbedClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelTypeView:
    """A model type's UI-facing metadata under a provider."""

    model_type: str
    label: str
    fields: list[FieldSpec]


@dataclass(frozen=True)
class ProviderTypeView:
    """A provider type's UI-facing metadata plus the model types it serves.

    ``fields`` are the provider's connection fields; ``model_types`` carries each
    supported capability with its own fields. ``supported_model_types`` is a flat
    view derived from ``model_types`` for the API and :func:`validate_provider`.
    """

    name: str
    label: str
    description: str
    type: ProviderType
    fields: list[FieldSpec]
    model_types: list[ModelTypeView]

    @property
    def supported_model_types(self) -> tuple[str, ...]:
        return tuple(mt.model_type for mt in self.model_types)


@dataclass(frozen=True)
class _ProviderEntry:
    """Internal registry record: a provider adapter and its handlers."""

    adapter_cls: type[ProviderTypeAdapter]
    handlers: dict[str, type[ModelTypeHandler]]

    def view(self) -> ProviderTypeView:
        cfg = self.adapter_cls.config
        model_types = sorted(
            (
                ModelTypeView(
                    model_type=h.config.model_type,
                    label=h.config.label,
                    fields=list(h.config.fields),
                )
                for h in self.handlers.values()
            ),
            key=lambda v: v.model_type,
        )
        return ProviderTypeView(
            name=cfg.name,
            label=cfg.label,
            description=cfg.description,
            type=cfg.type,
            fields=list(cfg.fields),
            model_types=model_types,
        )


_cache: dict[str, _ProviderEntry] | None = None


def _discover() -> dict[str, _ProviderEntry]:
    """Walk the package and build ``{provider_type: _ProviderEntry}``.

    A provider adapter lives in ``<provider>/base.py``; a model-type handler in
    ``<provider>/model_types/<cap>.py``. A handler is associated with the
    provider whose package (``...<provider>``) is a prefix of the handler's
    module path, so adding a capability is just dropping a module in the
    provider's ``model_types/`` folder.
    """
    import backend.plugins.provider_types as pkg

    # (provider_type name) -> (adapter class, provider package path).
    adapters: dict[str, tuple[type[ProviderTypeAdapter], str]] = {}
    # (handler class, its module name).
    handlers: list[tuple[type[ModelTypeHandler], str]] = []

    for module_info in pkgutil.walk_packages(pkg.__path__, prefix=f"{pkg.__name__}."):
        leaf = module_info.name.rsplit(".", 1)[-1]
        # Underscore-prefixed modules (``_remote``) are framework helpers.
        if leaf.startswith("_"):
            continue
        try:
            module = importlib.import_module(module_info.name)
        except Exception:
            logger.warning(
                "provider-type plugin %s failed to import; skipping",
                module_info.name,
                exc_info=True,
            )
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if inspect.isabstract(obj):
                continue
            if issubclass(obj, ProviderTypeAdapter) and obj is not ProviderTypeAdapter:
                cfg = getattr(obj, "config", None)
                name = getattr(cfg, "name", None)
                if isinstance(name, str) and name:
                    provider_pkg = module_info.name.rsplit(".", 1)[0]
                    adapters[name] = (obj, provider_pkg)
            elif issubclass(obj, ModelTypeHandler) and obj is not ModelTypeHandler:
                cfg = getattr(obj, "config", None)
                model_type = getattr(cfg, "model_type", None)
                if isinstance(model_type, str) and model_type:
                    handlers.append((obj, obj.__module__))

    registry: dict[str, _ProviderEntry] = {
        name: _ProviderEntry(adapter_cls=cls, handlers={})
        for name, (cls, _) in adapters.items()
    }
    for handler_cls, handler_module in handlers:
        for name, (_, provider_pkg) in adapters.items():
            if handler_module.startswith(f"{provider_pkg}."):
                model_type = handler_cls.config.model_type
                existing = registry[name].handlers.get(model_type)
                if existing is not None and existing is not handler_cls:
                    logger.warning(
                        "model type %r for provider %r registered by both %s and "
                        "%s; keeping the first discovered",
                        model_type,
                        name,
                        existing.__module__,
                        handler_cls.__module__,
                    )
                    break
                registry[name].handlers[model_type] = handler_cls
                break

    return registry


def _registry() -> dict[str, _ProviderEntry]:
    global _cache
    if _cache is None:
        _cache = _discover()
    return _cache


def _entry(name: str) -> _ProviderEntry:
    try:
        return _registry()[name]
    except KeyError:
        raise ValueError(f"Unknown provider type: {name!r}") from None


def list_provider_type_configs() -> list[ProviderTypeView]:
    """Return every discovered provider's UI-facing view, sorted by name."""
    return sorted(
        (entry.view() for entry in _registry().values()),
        key=lambda v: v.name,
    )


def get_provider_type_class(name: str) -> type[ProviderTypeAdapter]:
    """Return the provider adapter registered as *name* (``ValueError`` if unknown)."""
    return _entry(name).adapter_cls


def build_provider_type(
    name: str, values: dict[str, Any] | None = None
) -> ProviderTypeAdapter:
    """Instantiate the provider adapter registered as *name* with *values*."""
    return _entry(name).adapter_cls(values)


def resolve_config(name: str, values: dict[str, Any] | None) -> dict[str, Any]:
    """Resolve *values* against provider *name*'s connection field defaults.

    Connection-only: the capability (model-type) fields are resolved by
    :func:`validate_provider`, which also validates the selected capability.
    """
    return build_provider_type(name, values).resolved_config()


def _handler_cls(name: str, model_type: str) -> type[ModelTypeHandler]:
    entry = _entry(name)
    try:
        return entry.handlers[model_type]
    except KeyError:
        raise ValueError(
            f"Provider type {name!r} does not support model type {model_type!r}"
        ) from None


def _build_handler(
    name: str, model_type: str, values: dict[str, Any] | None
) -> ModelTypeHandler:
    """Build the model-type handler with the provider's resolved connection."""
    adapter = _entry(name).adapter_cls(values)
    handler_cls = _handler_cls(name, model_type)
    return handler_cls(values, adapter.resolve_connection())


def validate_provider(
    name: str,
    model_type: str,
    values: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate a provider type, capability, and config in one operation.

    Resolves the flat ``config`` against the union of the provider's connection
    fields and the selected model-type handler's fields. Raises ``ValueError``
    for an unknown provider type or an unsupported capability.
    """
    adapter = _entry(name).adapter_cls(values)
    handler = _build_handler(name, model_type, values)
    return {**adapter.resolved_config(), **handler.resolved_config()}


def resolve_embed_target(
    provider_type: str, model_type: str, values: dict[str, Any] | None
) -> ResolvedEmbedTarget:
    """Resolve a ``(provider_type, model_type, config)`` triple into an embed target."""
    return _build_handler(provider_type, model_type, values).resolve()


def build_embed_client(
    provider_type: str, model_type: str, values: dict[str, Any] | None
) -> EmbedClient:
    """Build the embed client for a ``(provider_type, model_type, config)`` triple.

    The single factory every embed path (the embed_chunks actor, compare and
    search) goes through instead of its own ``if provider == ...`` switch: it
    resolves the provider's connection, hands it to the selected model-type
    handler, and asks the handler to build its client (importing its heavy
    backend lazily inside that call).
    """
    return _build_handler(provider_type, model_type, values).build_embed_client()


def resolve_rerank_target(
    provider_type: str, model_type: str, values: dict[str, Any] | None
) -> ResolvedRerankTarget:
    """Resolve a ``(provider_type, model_type, config)`` triple into a rerank target.

    The reranking mirror of :func:`resolve_embed_target`. A model type that does
    not implement :meth:`ModelTypeHandler.resolve_rerank` raises rather than
    silently degrading.
    """
    return _build_handler(provider_type, model_type, values).resolve_rerank()
