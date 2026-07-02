"""Chunker plugin discovery.

Walks every module and subpackage under :mod:`backend.plugins.chunkers`
(``pkgutil.walk_packages``, so nested plugin packages are found too),
imports each one, and collects every concrete :class:`~backend.plugins.
chunkers.base.Chunker` subclass that declares a class-level ``config``. A
plugin that fails to import (missing dependency, syntax error, ...) is
logged and skipped rather than crashing discovery for every other plugin —
this endpoint and the actor must keep working even if one third-party
plugin is broken.

Discovery runs once per process and is cached at module level; call
:func:`list_chunker_configs` / :func:`build_chunker` freely, they are cheap
after the first call.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from typing import Any, Dict, List, Optional, Type

from backend.plugins.chunkers.base import Chunker, ChunkerConfig

logger = logging.getLogger(__name__)

# The chunker used when a pipeline run predates this feature (no recorded
# chunker) or omits one entirely.
DEFAULT_CHUNKER = "text_markdown"

# Modules that are part of the plugin framework itself, never plugins.
_FRAMEWORK_MODULES = frozenset({"base", "registry"})

_cache: Optional[Dict[str, Type[Chunker]]] = None


def _iter_plugin_modules():
    import backend.plugins.chunkers as chunkers_pkg

    for module_info in pkgutil.walk_packages(
        chunkers_pkg.__path__, prefix=f"{chunkers_pkg.__name__}."
    ):
        leaf_name = module_info.name.rsplit(".", 1)[-1]
        if leaf_name in _FRAMEWORK_MODULES:
            continue
        yield module_info.name


def _discover() -> Dict[str, Type[Chunker]]:
    discovered: Dict[str, Type[Chunker]] = {}

    for module_name in _iter_plugin_modules():
        try:
            module = importlib.import_module(module_name)
        except Exception:
            logger.warning(
                "chunker plugin %s failed to import; skipping", module_name,
                exc_info=True,
            )
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is Chunker or not issubclass(obj, Chunker):
                continue
            if inspect.isabstract(obj):
                continue
            config = getattr(obj, "config", None)
            if not isinstance(config, ChunkerConfig):
                continue
            existing = discovered.get(config.name)
            if existing is not None and existing is not obj:
                logger.warning(
                    "chunker plugin name %r registered by both %s and %s; "
                    "keeping the first one discovered",
                    config.name, existing.__module__, obj.__module__,
                )
                continue
            discovered[config.name] = obj

    return discovered


def _registry() -> Dict[str, Type[Chunker]]:
    global _cache
    if _cache is None:
        _cache = _discover()
    return _cache


def list_chunker_configs() -> List[ChunkerConfig]:
    """Return every discovered chunker's static config, sorted by name."""
    return sorted(
        (cls.config for cls in _registry().values()), key=lambda c: c.name
    )


def get_chunker_class(name: str) -> Type[Chunker]:
    """Return the ``Chunker`` subclass registered as *name*.

    Raises ``ValueError`` when *name* is not a discovered chunker.
    """
    try:
        return _registry()[name]
    except KeyError:
        raise ValueError(f"Unknown chunker: {name!r}") from None


def build_chunker(name: str, settings: Dict[str, Any]) -> Chunker:
    """Instantiate the chunker registered as *name* with *settings*."""
    return get_chunker_class(name)(settings)
