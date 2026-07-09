"""Validation strategy plugins for the ``validate_source`` actor.

One strategy per dataset source type: ``web`` (URL normalization + same-origin
gate) and ``local`` (path resolution + exists/readable checks). Drop a new
strategy module here — a concrete subclass of
:class:`backend.plugins.validate_source.base.SourceValidationStrategy` with a
class-level ``config`` — and it is auto-discovered by
:mod:`backend.plugins.validate_source.registry` at process start; no manual
registration step required.
"""

from __future__ import annotations
