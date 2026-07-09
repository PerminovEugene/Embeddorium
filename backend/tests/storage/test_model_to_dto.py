"""ORM -> domain mapping for chunk position offsets."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from backend.shared.storage.sql.model_to_dto import _to_chunk
from backend.shared.storage.sql.models.chunk import DocumentChunkORM


def _orm_chunk(**overrides) -> DocumentChunkORM:
    defaults = dict(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        text="some text",
        chunk_index=0,
        chunk_type="passage",
        chunk_metadata={},
        status="pending",
        created_at=datetime.now(UTC),
        start_offset=None,
        end_offset=None,
    )
    defaults.update(overrides)
    return DocumentChunkORM(**defaults)


def test_to_chunk_maps_offsets():
    orm = _orm_chunk(start_offset=12, end_offset=21)
    chunk = _to_chunk(orm)
    assert chunk.start_offset == 12
    assert chunk.end_offset == 21


def test_to_chunk_keeps_null_offsets_none():
    chunk = _to_chunk(_orm_chunk())
    assert chunk.start_offset is None
    assert chunk.end_offset is None
