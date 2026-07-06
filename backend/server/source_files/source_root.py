"""Resolve and guard paths against the ingestion **source root**.

The actors read local files from a single directory tree that is mounted into
their containers (``./sources -> /app/sources`` in docker-compose). The UI lets
the user browse and pick files/folders *inside* that tree, and stores the
selection as paths **relative to the source root**. Both the browse endpoint
(``source_files.router``) and the pipeline seeder (``pipeline.launch``) resolve
those relative paths back to real files through this module so the server and
the actors agree on one anchor.

``SOURCE_ROOT`` overrides the directory (env var); it defaults to ``sources``
resolved against the process CWD, which is ``/app`` in every container, giving
``/app/sources`` — the same absolute path the actors see through their mount.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_source_root() -> Path:
    """Absolute path of the directory the UI is allowed to browse/select from."""
    return Path(os.getenv("SOURCE_ROOT", "sources")).resolve()


def resolve_for_seed(path: str) -> Path:
    """Resolve a stored dataset path to a real file path for the file actor.

    Relative entries (what the source-file browser produces, e.g.
    ``xml.2026.en/act.xml``) are joined onto the source root. Absolute entries
    — the admin/API use-case and what older callers pass — are returned as-is,
    since joining an absolute path onto a root discards the root anyway.
    """
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return get_source_root() / candidate


def safe_resolve_within_root(rel: str) -> Path:
    """Resolve *rel* (relative to the source root) and reject path traversal.

    Raises ``ValueError`` if the result escapes the source root (e.g. via
    ``..`` segments or an absolute path). Used by the browse endpoint, which
    must never expose files outside the mounted source tree.
    """
    root = get_source_root()
    resolved = (root / rel).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"Path {rel!r} escapes the source root")
    return resolved
