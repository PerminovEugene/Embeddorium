"""Discovery/lookup for parse_source strategy plugins.

Discovery runs once per process and is cached at module level (see
:mod:`backend.plugins._strategy_discovery`). Strategies carry per-run settings,
so :func:`build_parse_strategy` instantiates the class with a resolved settings
dict — mirroring :func:`backend.plugins.chunkers.registry.build_chunker`.
"""

from __future__ import annotations

from typing import Any

from backend.plugins._strategy_discovery import discover_strategies
from backend.plugins.parse_source.base import ParseStrategy, ParseStrategyConfig

# The strategy used when a run does not pin a specific one. There is a single
# built-in strategy today; the constant keeps the actor from hard-coding a name.
DEFAULT_PARSE_STRATEGY = "content_type"

_cache: dict[str, type[ParseStrategy]] | None = None


def _registry() -> dict[str, type[ParseStrategy]]:
    global _cache
    if _cache is None:
        import backend.plugins.parse_source as pkg

        _cache = discover_strategies(pkg, ParseStrategy)
    return _cache


def list_parse_strategy_configs() -> list[ParseStrategyConfig]:
    """Return every discovered strategy's static config, sorted by name."""
    return sorted((cls.config for cls in _registry().values()), key=lambda c: c.name)


def get_parse_strategy_class(name: str) -> type[ParseStrategy]:
    """Return the strategy class registered as *name* (``ValueError`` if unknown)."""
    try:
        return _registry()[name]
    except KeyError:
        raise ValueError(f"Unknown parse_source strategy: {name!r}") from None


def build_parse_strategy(
    name: str, settings: dict[str, Any] | None = None
) -> ParseStrategy:
    """Instantiate the strategy registered as *name* with *settings*."""
    return get_parse_strategy_class(name)(settings)
