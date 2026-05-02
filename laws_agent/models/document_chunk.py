from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    from laws_agent.models.document import Document


class DocumentChunk(BaseModel):
    id: Optional[uuid.UUID] = None
    document_id: uuid.UUID
    text: str
    chunk_index: int
    created_at: Optional[datetime] = None
    document: Optional[Document] = None
