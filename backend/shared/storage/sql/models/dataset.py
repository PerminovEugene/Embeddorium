from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    ARRAY,
    DateTime,
    Text,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.storage.sql.models.base import Base


class DatasetORM(Base):
    """A dataset row, discriminated by ``source_type``.

    Variant-specific columns (web vs. local) are flat and nullable rather
    than a JSONB blob, so every field stays queryable like the rest of this
    schema; only the columns relevant to a row's ``source_type`` are set.
    """

    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)

    # web
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # local
    paths: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sql_text("now()"),
    )
