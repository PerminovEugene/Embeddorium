from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel


class CrawlTargetStatus(StrEnum):
    DISCOVERED = "discovered"
    QUEUED = "queued"
    PROCESSING = "processing"
    PROCESSED = "processed"
    SKIPPED = "skipped"
    FAILED = "failed"


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