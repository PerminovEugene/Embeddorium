from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel


class DiscoveredLinkStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"


class DiscoveredLink(BaseModel):
    """A link found while parsing a document, persisted before it is scheduled
    to the crawl frontier (so scheduling is recoverable)."""

    id: Optional[uuid.UUID] = None
    source_document_id: Optional[uuid.UUID] = None
    source_chunk_id: Optional[uuid.UUID] = None
    raw_url: str
    normalized_url: str
    anchor_text: Optional[str] = None
    context_text: Optional[str] = None
    status: DiscoveredLinkStatus = DiscoveredLinkStatus.PENDING
    created_at: Optional[datetime] = None
