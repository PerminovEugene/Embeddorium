from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from laws_agent.storage.sql.models.document import DocumentORM


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
from laws_agent.storage.sql.models.base import Base
# from laws_agent.storage.sql.models.document import DocumentORM

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
    links: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
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