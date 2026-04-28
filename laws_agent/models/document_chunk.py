from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from laws_agent.parsers.link_extractor import LinkInfo

if TYPE_CHECKING:
    from laws_agent.models.document import Document


class DocumentChunk(BaseModel):
    id: Optional[uuid.UUID] = None
    document_id: uuid.UUID
    text: str
    links: list[LinkInfo] = Field(default_factory=list)
    chunk_index: int
    created_at: Optional[datetime] = None
    document: Optional[Document] = None
