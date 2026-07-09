"""Discovery/lookup for validate_source strategy plugins.

Discovery runs once per process and is cached at module level; strategies are
stateless, so :func:`build_validation_strategy` just instantiates the class.
"""

from __future__ import annotations

from backend.plugins._strategy_discovery import discover_strategies
from backend.plugins.validate_source.base import (
    SourceValidationStrategy,
    ValidationStrategyConfig,
)

_cache: dict[str, type[SourceValidationStrategy]] | None = None


def _registry() -> dict[str, type[SourceValidationStrategy]]:
    global _cache
    if _cache is None:
        import backend.plugins.validate_source as pkg

        _cache = discover_strategies(pkg, SourceValidationStrategy)
    return _cache


def list_validation_strategy_configs() -> list[ValidationStrategyConfig]:
    """Return every discovered strategy's static config, sorted by name."""
    return sorted((cls.config for cls in _registry().values()), key=lambda c: c.name)


def get_validation_strategy_class(name: str) -> type[SourceValidationStrategy]:
    """Return the strategy class registered as *name* (``ValueError`` if unknown)."""
    try:
        return _registry()[name]
    except KeyError:
        raise ValueError(f"Unknown validate_source strategy: {name!r}") from None


def build_validation_strategy(name: str) -> SourceValidationStrategy:
    """Instantiate the strategy registered as *name*."""
    return get_validation_strategy_class(name)()
