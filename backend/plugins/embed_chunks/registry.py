"""Discovery/lookup for embed_chunks strategy plugins.

Discovery runs once per process and is cached at module level (see
:mod:`backend.plugins._strategy_discovery`). Strategies carry the run's
provider snapshot as settings, so :func:`build_embed_strategy` instantiates the
class with a resolved settings dict — mirroring
:func:`backend.plugins.chunkers.registry.build_chunker`.
"""

from __future__ import annotations

from typing import Any

from backend.plugins._strategy_discovery import discover_strategies
from backend.plugins.embed_chunks.base import EmbedStrategy, EmbedStrategyConfig

# The strategy used when a run does not pin a specific one. There is a single
# built-in strategy today; the constant keeps the launcher from hard-coding a name.
DEFAULT_EMBED_STRATEGY = "standard"

_cache: dict[str, type[EmbedStrategy]] | None = None


def _registry() -> dict[str, type[EmbedStrategy]]:
    global _cache
    if _cache is None:
        import backend.plugins.embed_chunks as pkg

        _cache = discover_strategies(pkg, EmbedStrategy)
    return _cache


def list_embed_strategy_configs() -> list[EmbedStrategyConfig]:
    """Return every discovered strategy's static config, sorted by name."""
    return sorted((cls.config for cls in _registry().values()), key=lambda c: c.name)


def get_embed_strategy_class(name: str) -> type[EmbedStrategy]:
    """Return the strategy class registered as *name* (``ValueError`` if unknown)."""
    try:
        return _registry()[name]
    except KeyError:
        raise ValueError(f"Unknown embed_chunks strategy: {name!r}") from None


def build_embed_strategy(
    name: str, settings: dict[str, Any] | None = None
) -> EmbedStrategy:
    """Instantiate the strategy registered as *name* with *settings*."""
    return get_embed_strategy_class(name)(settings)
