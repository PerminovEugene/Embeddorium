from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field
from backend.plugins.structured_data import JsonObject, JsonValue

if TYPE_CHECKING:
    from backend.shared.models.document_chunk import DocumentChunk


class Document(BaseModel):
    id: Optional[uuid.UUID] = None
    source_url: str

    # Real document language ("unknown" until detection is added).
    language: str = "unknown"

    # Fetch/parse provenance (see migration 005). The dataset this document
    # belongs to is reached via crawl_target_id -> CrawlTarget.pipeline_id ->
    # PipelineRun.dataset, not stored redundantly here (see migration 024).
    crawl_target_id: Optional[uuid.UUID] = None
    normalized_url: Optional[str] = None
    final_url: Optional[str] = None
    http_status: Optional[int] = None
    content_type: Optional[str] = None
    content_hash: Optional[str] = None
    text_hash: Optional[str] = None
    parser_version: Optional[str] = None
    parser_name: Optional[str] = None
    parser_output_format: Optional[str] = None
    parser_metadata: JsonObject = Field(default_factory=dict)
    parser_intermediate: JsonValue = None
    chunker_version: Optional[str] = None
    retrieved_at: Optional[datetime] = None

    # Path (relative to PIPELINE_RUNS_DIR) of the normalised parsed-text file,
    # written by parse_source and read by chunk_document.
    text_path: Optional[str] = None

    created_at: Optional[datetime] = None
    chunks: list[DocumentChunk] = Field(default_factory=list)
