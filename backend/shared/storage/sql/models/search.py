from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.storage.sql.models.base import Base


class SearchORM(Base):
    __tablename__ = "searches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # The pipeline run whose collection/embedding model this query was run
    # against. FK to pipeline_runs(id) ON DELETE CASCADE.
    pipeline_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # The user input text this search was launched with. FK to
    # search_inputs(id) ON DELETE CASCADE.
    user_input_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    # e.g. {"top_n": 10, "search_method": "embedding"}.
    search_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=sql_text("'{}'::jsonb"),
    )
    # The list of result hits returned for this query.
    results: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default=sql_text("'[]'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sql_text("now()"),
    )
