"""Discovery/lookup for filter_documents strategy plugins.

Discovery runs once per process and is cached at module level (see
:mod:`backend.plugins._strategy_discovery`). Strategies carry per-run settings,
so :func:`build_filter_strategy` instantiates the class with a resolved
settings dict — mirroring :func:`backend.plugins.chunkers.registry.build_chunker`.
"""

from __future__ import annotations

from typing import Any

from backend.plugins._strategy_discovery import discover_strategies
from backend.plugins.filter_documents.base import FilterStrategy, FilterStrategyConfig

# The strategy used when a run does not pin a specific one. There is a single
# built-in strategy today; the constant keeps the actor from hard-coding a name.
DEFAULT_FILTER_STRATEGY = "keyword"

_cache: dict[str, type[FilterStrategy]] | None = None


def _registry() -> dict[str, type[FilterStrategy]]:
    global _cache
    if _cache is None:
        import backend.plugins.filter_documents as pkg

        _cache = discover_strategies(pkg, FilterStrategy)
    return _cache


def list_filter_strategy_configs() -> list[FilterStrategyConfig]:
    """Return every discovered strategy's static config, sorted by name."""
    return sorted((cls.config for cls in _registry().values()), key=lambda c: c.name)


def get_filter_strategy_class(name: str) -> type[FilterStrategy]:
    """Return the strategy class registered as *name* (``ValueError`` if unknown)."""
    try:
        return _registry()[name]
    except KeyError:
        raise ValueError(f"Unknown filter_documents strategy: {name!r}") from None


def build_filter_strategy(
    name: str, settings: dict[str, Any] | None = None
) -> FilterStrategy:
    """Instantiate the strategy registered as *name* with *settings*."""
    return get_filter_strategy_class(name)(settings)
