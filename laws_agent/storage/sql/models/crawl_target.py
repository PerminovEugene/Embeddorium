from __future__ import annotations

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from laws_agent.storage.sql.models.chunk import DocumentChunkORM
    from laws_agent.storage.sql.models.document import DocumentORM

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
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

from laws_agent.storage.sql.models.base import Base


class CrawlTargetORM(Base):
    __tablename__ = "crawl_targets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    group: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    original_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    normalized_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="discovered",
    )
    depth: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    log_dir: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    skip_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sql_text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sql_text("now()"),
        onupdate=sql_text("now()"),
    )

    document: Mapped[Optional["DocumentORM"]] = relationship(
        "DocumentORM",
        foreign_keys=[document_id],
    )
    parent_chunk: Mapped[Optional["DocumentChunkORM"]] = relationship(
        "DocumentChunkORM",
        back_populates="crawl_targets",
        foreign_keys=[parent_chunk_id],
    )
    parent_document: Mapped[Optional["DocumentORM"]] = relationship(
        "DocumentORM",
        foreign_keys=[parent_document_id],
    )
