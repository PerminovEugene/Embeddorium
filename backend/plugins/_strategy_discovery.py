"""Shared plugin discovery for per-actor strategy packages.

Mirrors the discovery pattern established by
:mod:`backend.plugins.chunkers.registry`: walk every module and subpackage
under a strategy package, import each one, and collect every concrete
subclass of the package's base class that declares a class-level ``config``
with a ``name``. A plugin that fails to import (missing dependency, syntax
error, ...) is logged and skipped rather than crashing discovery for every
other plugin.

Each strategy package (one per actor — see ``backend/plugins/validate_source``
and ``backend/plugins/fetch_source``) keeps its own module-level cache and
calls :func:`discover_strategies` once per process.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from types import ModuleType

logger = logging.getLogger(__name__)

# Modules that are part of a strategy package's framework, never plugins.
_FRAMEWORK_MODULES = frozenset({"base", "registry"})


def _iter_plugin_modules(package: ModuleType):
    for module_info in pkgutil.walk_packages(
        package.__path__, prefix=f"{package.__name__}."
    ):
        leaf_name = module_info.name.rsplit(".", 1)[-1]
        if leaf_name in _FRAMEWORK_MODULES or leaf_name.startswith("_"):
            continue
        yield module_info.name


def discover_strategies(package: ModuleType, base_cls: type) -> dict[str, type]:
    """Return ``{config.name: strategy_class}`` for every plugin in *package*."""
    discovered: dict[str, type] = {}

    for module_name in _iter_plugin_modules(package):
        try:
            module = importlib.import_module(module_name)
        except Exception:
            logger.warning(
                "strategy plugin %s failed to import; skipping",
                module_name,
                exc_info=True,
            )
            continue

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is base_cls or not issubclass(obj, base_cls):
                continue
            if inspect.isabstract(obj):
                continue
            config = getattr(obj, "config", None)
            name = getattr(config, "name", None)
            if not isinstance(name, str) or not name:
                continue
            existing = discovered.get(name)
            if existing is not None and existing is not obj:
                logger.warning(
                    "strategy name %r registered by both %s and %s; "
                    "keeping the first one discovered",
                    name,
                    existing.__module__,
                    obj.__module__,
                )
                continue
            discovered[name] = obj

    return discovered
