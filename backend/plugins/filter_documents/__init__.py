"""Filter strategy plugins for the ``filter_documents`` actor.

Decides whether a fetched document is relevant enough to advance down the
pipeline. Drop a new strategy module here — a concrete subclass of
:class:`backend.plugins.filter_documents.base.FilterStrategy` with a
class-level ``config`` — and it is auto-discovered by
:mod:`backend.plugins.filter_documents.registry` at process start; no manual
registration step required.

The built-in ``keyword`` strategy (title/body keyword matching) lives
alongside this file as the reference implementation. See ``base.py`` for the
plugin interface and ``registry.py`` for discovery.
"""

from __future__ import annotations
