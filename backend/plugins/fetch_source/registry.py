"""Discovery/lookup for fetch_source strategy plugins.

Discovery runs once per process and is cached at module level; strategies are
stateless, so :func:`build_fetch_strategy` just instantiates the class.
"""

from __future__ import annotations

from backend.plugins._strategy_discovery import discover_strategies
from backend.plugins.fetch_source.base import FetchStrategyConfig, SourceFetchStrategy

_cache: dict[str, type[SourceFetchStrategy]] | None = None


def _registry() -> dict[str, type[SourceFetchStrategy]]:
    global _cache
    if _cache is None:
        import backend.plugins.fetch_source as pkg

        _cache = discover_strategies(pkg, SourceFetchStrategy)
    return _cache


def list_fetch_strategy_configs() -> list[FetchStrategyConfig]:
    """Return every discovered strategy's static config, sorted by name."""
    return sorted((cls.config for cls in _registry().values()), key=lambda c: c.name)


def get_fetch_strategy_class(name: str) -> type[SourceFetchStrategy]:
    """Return the strategy class registered as *name* (``ValueError`` if unknown)."""
    try:
        return _registry()[name]
    except KeyError:
        raise ValueError(f"Unknown fetch_source strategy: {name!r}") from None


def build_fetch_strategy(name: str) -> SourceFetchStrategy:
    """Instantiate the strategy registered as *name*."""
    return get_fetch_strategy_class(name)()
