from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.shared.models.document import Document


class DocumentChunk(BaseModel):
    id: Optional[uuid.UUID] = None
    document_id: uuid.UUID
    text: str
    chunk_index: int
    # "passage" for generic text chunks; legal_body/act_title/amendment_history/
    # legal_metadata for chunks produced by the legal XML chunker.
    chunk_type: str = "passage"
    chunk_metadata: dict = Field(default_factory=dict)
    # Embedding lifecycle: "pending" until embed_chunks upserts this chunk's
    # vector into Qdrant, then "embedded". See
    # UnitOfWork.finalize_target_if_all_chunks_embedded.
    status: str = "pending"
    created_at: Optional[datetime] = None
    document: Optional[Document] = None
