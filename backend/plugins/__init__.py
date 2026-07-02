"""Pluggable extension points for the ingestion pipeline.

Currently home to ``backend.plugins.chunkers`` (document chunking strategies).
Kept as its own top-level package — separate from ``backend.shared`` — so it
is obvious at a glance which code is a swappable plugin surface versus core
pipeline logic, and so future plugin kinds (parsers, filters, ...) have an
unambiguous place to live.
"""

from __future__ import annotations
