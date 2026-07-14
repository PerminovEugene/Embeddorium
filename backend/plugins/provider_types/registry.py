"""Discovery/lookup for provider-type adapters.

Discovery runs once per process and is cached at module level (see
:mod:`backend.plugins._strategy_discovery`), mirroring every other plugin
registry. On top of the usual ``list``/``get``/``build`` trio this module
exposes two convenience helpers the rest of the app dispatches through instead
of hardcoding provider-type branches:

- :func:`resolve_config` — resolve a raw provider ``config`` dict against the
  selected adapter's field defaults (used when persisting a provider).
- :func:`resolve_embed_target` — turn a ``(provider_type, config)`` pair into a
  concrete :class:`~backend.plugins.provider_types.base.ResolvedEmbedTarget`,
  falling back to the local HuggingFace path for an unknown/legacy type so old
  runs keep working.
"""

from __future__ import annotations

from typing import Any

from backend.plugins._strategy_discovery import discover_strategies
from backend.plugins.provider_types.base import (
    ProviderTypeAdapter,
    ProviderTypeConfig,
    ResolvedEmbedTarget,
    ResolvedRerankTarget,
)
from backend.shared.models.provider import ModelType

# The local model an unknown/legacy provider type embeds with — keeps the
# pre-plugin behavior where anything that wasn't ollama/mock/fastembed was
# treated as a local HuggingFace model.
_HUGGINGFACE_DEFAULT_MODEL = "Qwen/Qwen3-Embedding-8B"

_cache: dict[str, type[ProviderTypeAdapter]] | None = None


def _registry() -> dict[str, type[ProviderTypeAdapter]]:
    global _cache
    if _cache is None:
        import backend.plugins.provider_types as pkg

        _cache = discover_strategies(pkg, ProviderTypeAdapter)
    return _cache


def list_provider_type_configs() -> list[ProviderTypeConfig]:
    """Return every discovered adapter's static config, sorted by name."""
    return sorted((cls.config for cls in _registry().values()), key=lambda c: c.name)


def get_provider_type_class(name: str) -> type[ProviderTypeAdapter]:
    """Return the adapter registered as *name* (``ValueError`` if unknown)."""
    try:
        return _registry()[name]
    except KeyError:
        raise ValueError(f"Unknown provider type: {name!r}") from None


def build_provider_type(
    name: str, values: dict[str, Any] | None = None
) -> ProviderTypeAdapter:
    """Instantiate the adapter registered as *name* with *values*."""
    return get_provider_type_class(name)(values)


def resolve_config(name: str, values: dict[str, Any] | None) -> dict[str, Any]:
    """Return *values* resolved against adapter *name*'s field defaults.

    Fills each declared field's default for missing keys and drops keys the
    adapter doesn't declare, so a stored provider's ``config`` always matches
    the adapter's fields. Raises ``ValueError`` for an unknown provider type.
    """
    return build_provider_type(name, values).resolved_config()


def validate_provider(
    name: str,
    model_type: ModelType,
    values: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate an adapter name, capability, and config in one operation."""
    adapter_cls = get_provider_type_class(name)
    if model_type not in adapter_cls.config.supported_model_types:
        raise ValueError(
            f"Provider type {name!r} does not support model type {model_type!r}"
        )
    return adapter_cls(values).resolved_config()


def resolve_embed_target(
    provider_type: str, values: dict[str, Any] | None
) -> ResolvedEmbedTarget:
    """Resolve a ``(provider_type, config)`` pair into an embed target.

    An unknown/legacy ``provider_type`` (e.g. a snapshot from before the plugin
    rework) falls back to the local HuggingFace model named in the config, so
    existing runs keep resolving instead of erroring.
    """
    try:
        adapter_cls = get_provider_type_class(provider_type)
    except ValueError:
        model = (values or {}).get("model_name") or (values or {}).get("model")
        return ResolvedEmbedTarget(
            provider="huggingface",
            model=model or _HUGGINGFACE_DEFAULT_MODEL,
        )
    return adapter_cls(values).resolve()


def resolve_rerank_target(
    provider_type: str, values: dict[str, Any] | None
) -> ResolvedRerankTarget:
    """Resolve a ``(provider_type, config)`` pair into a rerank target.

    The mirror of :func:`resolve_embed_target` for the reranking capability.
    Unlike the embed path there is no legacy fallback: a reranker provider is a
    post-plugin concept, so an unknown ``provider_type`` (or one that does not
    implement :meth:`resolve_rerank`) raises rather than silently degrading.
    """
    adapter_cls = get_provider_type_class(provider_type)
    return adapter_cls(values).resolve_rerank()
