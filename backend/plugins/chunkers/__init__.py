"""Chunker plugin package.

Drop a chunker plugin here — either a single module or a subpackage — and it
is auto-discovered by :mod:`backend.plugins.chunkers.registry` at process
start: no manual registration step required. A plugin module just needs to
define a concrete subclass of :class:`backend.plugins.chunkers.base.Chunker`
with a class-level ``config`` (a :class:`~backend.plugins.chunkers.base.
ChunkerConfig`) describing it.

See ``base.py`` for the plugin interface and ``registry.py`` for discovery.
The built-in chunkers (``text_markdown``, ``text_section``,
``text_recursive``, ``text_fixed``, ``legal_xml``) live alongside this file
as the reference implementations.
"""

from __future__ import annotations
