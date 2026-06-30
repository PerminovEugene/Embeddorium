from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.shared.models.document_chunk import DocumentChunk


class Document(BaseModel):
    id: Optional[uuid.UUID] = None
    source_url: str

    # Real document language ("unknown" until detection is added), NOT the crawl group.
    language: str = "unknown"

    # Crawl context + fetch/parse provenance (see migration 005).
    group: Optional[str] = None
    crawl_target_id: Optional[uuid.UUID] = None
    normalized_url: Optional[str] = None
    final_url: Optional[str] = None
    http_status: Optional[int] = None
    content_type: Optional[str] = None
    content_hash: Optional[str] = None
    text_hash: Optional[str] = None
    parser_version: Optional[str] = None
    chunker_version: Optional[str] = None
    retrieved_at: Optional[datetime] = None

    # Normalized parsed text (carried from parse_source to chunk_document).
    text: Optional[str] = None

    created_at: Optional[datetime] = None
    chunks: list[DocumentChunk] = Field(default_factory=list)
