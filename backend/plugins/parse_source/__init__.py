"""Parse strategy plugins for the ``parse_source`` actor.

Turns a fetched source's raw content into normalized text. Drop a new strategy
module here — a concrete subclass of
:class:`backend.plugins.parse_source.base.ParseStrategy` with a class-level
``config`` — and it is auto-discovered by
:mod:`backend.plugins.parse_source.registry` at process start; no manual
registration step required.

The built-in ``content_type`` strategy (override-else-content-type parser
selection) lives alongside this file as the reference implementation. See
``base.py`` for the plugin interface and ``registry.py`` for discovery.
"""

from __future__ import annotations
