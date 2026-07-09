from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.shared.storage.sql.models.document import DocumentORM
    from backend.shared.storage.sql.models.crawl_target import CrawlTargetORM


import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Text,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from backend.shared.storage.sql.models.base import Base

class DocumentChunkORM(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    # Legal chunk classification + structured legal metadata. Defaults keep
    # rows written by the generic text splitter (and pre-migration rows) valid.
    chunk_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=sql_text("'passage'"),
    )
    chunk_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=sql_text("'{}'"),
    )
    # Character offsets of the chunk within the parsed source text (start
    # inclusive, end exclusive). Nullable: pre-migration rows and chunkers
    # that don't track positions leave them NULL.
    start_offset: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    end_offset: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    # Embedding lifecycle for this chunk: "pending" until embed_chunks upserts
    # its vector into Qdrant, then "embedded". A crawl target only reaches
    # PROCESSED once every chunk of its document is "embedded" — see
    # UnitOfWork.finalize_target_if_all_chunks_embedded.
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=sql_text("'pending'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sql_text("now()"),
    )

    document: Mapped["DocumentORM"] = relationship(
        "DocumentORM",
        back_populates="chunks",
    )
    crawl_targets: Mapped[list["CrawlTargetORM"]] = relationship(
        "CrawlTargetORM",
        back_populates="parent_chunk",
        cascade="all, delete-orphan",
        foreign_keys="CrawlTargetORM.parent_chunk_id",
    )