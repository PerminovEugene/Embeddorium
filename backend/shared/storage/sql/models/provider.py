from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Integer,
    Text,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.storage.sql.models.base import Base


class ProviderORM(Base):
    """A provider row, discriminated by ``provider_type``.

    Variant-specific columns (ollama vs. remote vs. mock) are flat and
    nullable rather than a JSONB blob, so every field stays queryable like
    the rest of this schema; only the columns relevant to a row's
    ``provider_type`` are set.
    """

    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    provider_type: Mapped[str] = mapped_column(Text, nullable=False)
    model_type: Mapped[str] = mapped_column(Text, nullable=False)

    # ollama
    port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ollama + remote
    model_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # remote
    base_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    organization: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sql_text("now()"),
    )
