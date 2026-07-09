"""Fetch strategy plugins for the merged ``fetch_source`` actor.

One strategy per dataset source type: ``web`` (HTTP fetch, routes onward to
``parse_source``) and ``local`` (file read, routes onward to
``filter_documents``). Drop a new strategy module here — a concrete subclass
of :class:`backend.plugins.fetch_source.base.SourceFetchStrategy` with a
class-level ``config`` — and it is auto-discovered by
:mod:`backend.plugins.fetch_source.registry` at process start; no manual
registration step required.
"""

from __future__ import annotations
