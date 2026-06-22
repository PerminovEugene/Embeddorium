"""Failure classification for fetching.

The pipeline must retry only failures that might succeed later. We split every
failure into ``TRANSIENT`` (retry with backoff) and ``PERMANENT`` (give up).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Optional


class FailureKind(StrEnum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"


class FetchFailure(Exception):
    """Raised by the fetcher with an explicit transient/permanent classification."""

    def __init__(
        self,
        kind: FailureKind,
        message: str,
        *,
        status: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status = status

    @property
    def is_transient(self) -> bool:
        return self.kind is FailureKind.TRANSIENT


# 429 (rate limited) + 5xx are worth retrying; other 4xx are not.
_TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})


def classify_status(status: int) -> FailureKind:
    if status in _TRANSIENT_STATUSES or 500 <= status <= 599:
        return FailureKind.TRANSIENT
    return FailureKind.PERMANENT
