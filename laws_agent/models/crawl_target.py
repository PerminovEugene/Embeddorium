from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel


class CrawlTargetStatus(StrEnum):
    DISCOVERED = "discovered"
    QUEUED = "queued"

    # Pipeline stages (each owned by one actor via a compare-and-set lock).
    FETCHING = "fetching"
    FETCHED = "fetched"
    PARSING = "parsing"
    PARSED = "parsed"
    CHUNKING = "chunking"
    CHUNKED = "chunked"
    SCHEDULING = "scheduling"
    PROCESSED = "processed"

    # Terminal / skip states.
    SKIPPED = "skipped"
    SKIPPED_UNSUPPORTED = "skipped_unsupported"
    FAILED_TRANSIENT = "failed_transient"
    FAILED_PERMANENT = "failed_permanent"

    # Legacy statuses kept for backwards compatibility with existing rows.
    PROCESSING = "processing"
    FAILED = "failed"


# Statuses from which a URL should NOT be re-queued by the frontier manager.
# Transient failures (and the legacy FAILED) stay re-queueable.
TERMINAL_OR_ACTIVE_STATUSES = frozenset(
    s
    for s in CrawlTargetStatus
    if s not in (CrawlTargetStatus.FAILED_TRANSIENT, CrawlTargetStatus.FAILED)
)


class CrawlTarget(BaseModel):
    id: Optional[uuid.UUID] = None

    group: str
    original_url: str
    normalized_url: str

    status: CrawlTargetStatus = CrawlTargetStatus.DISCOVERED

    depth: int = 0

    document_id: Optional[uuid.UUID] = None

    parent_chunk_id: Optional[uuid.UUID] = None
    parent_document_id: Optional[uuid.UUID] = None

    error: Optional[str] = None
    skip_reason: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None