"""Embed strategy plugins for the ``embed_chunks`` actor.

Resolves a run's embedding-provider snapshot into the concrete
``(provider, model, mock_dim)`` triple the worker loads a model from. Drop a
new strategy module here — a concrete subclass of
:class:`backend.plugins.embed_chunks.base.EmbedStrategy` with a class-level
``config`` — and it is auto-discovered by
:mod:`backend.plugins.embed_chunks.registry` at process start; no manual
registration step required.

The built-in ``standard`` strategy (provider-snapshot parsing) lives alongside
this file as the reference implementation. See ``base.py`` for the plugin
interface and ``registry.py`` for discovery.
"""

from __future__ import annotations
