from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from laws_agent.models.document_chunk import DocumentChunk


class Document(BaseModel):
    id: Optional[uuid.UUID] = None
    source_url: str
    language: str
    created_at: Optional[datetime] = None
    chunks: list[DocumentChunk] = Field(default_factory=list)
