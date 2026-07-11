"""Shared helpers for the pipeline-run service.

Only genuinely cross-cutting helpers live here; anything unique to a single
service operation stays in that operation's own module.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException

# Statuses that mean a run has finished (successfully or not). Reaching one of
# these via ``PATCH`` also stamps ``finished_at``.
TERMINAL_STATUSES = {"completed", "failed"}


def parse_run_id(run_id: str) -> uuid.UUID:
    """Parse a path ``run_id`` into a ``UUID``, 404-ing on a malformed value."""
    try:
        return uuid.UUID(run_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Pipeline run not found")
