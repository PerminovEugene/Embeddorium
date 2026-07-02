from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SourceFetch(BaseModel):
    """Raw HTTP fetch result + provenance, produced by ``fetch_source`` and
    consumed by ``parse_source``."""

    id: Optional[uuid.UUID] = None
    crawl_target_id: uuid.UUID
    final_url: str
    http_status: int
    content_type: Optional[str] = None
    content_hash: str
    raw_content_path: Optional[str] = None
    redirect_chain: list[str] = Field(default_factory=list)
    fetched_at: Optional[datetime] = None
