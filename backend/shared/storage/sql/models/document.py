from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.shared.storage.sql.models.chunk import DocumentChunkORM

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.shared.storage.sql.models.base import Base

class DocumentORM(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    language: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default="unknown",
    )

    # Crawl context + fetch/parse provenance (migration 005).
    group: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    crawl_target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    normalized_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parser_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chunker_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    text_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sql_text("now()"),
    )

    chunks: Mapped[list["DocumentChunkORM"]] = relationship(
        "DocumentChunkORM",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="select",
    )


