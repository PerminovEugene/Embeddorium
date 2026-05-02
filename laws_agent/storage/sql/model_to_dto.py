from __future__ import annotations

from laws_agent.models import Document, DocumentChunk
from laws_agent.storage.sql.models.document import DocumentORM
from laws_agent.storage.sql.models.chunk import DocumentChunkORM

def _to_document(orm: DocumentORM, include_chunks: bool = False) -> Document:
    return Document(
        id=orm.id,
        source_url=orm.source_url,
        language=orm.language,
        created_at=orm.created_at,
        chunks=[_to_chunk(chunk) for chunk in orm.chunks] if include_chunks else [],
    )


def _to_chunk(orm: DocumentChunkORM) -> DocumentChunk:
    return DocumentChunk(
        id=orm.id,
        document_id=orm.document_id,
        text=orm.text,
        chunk_index=orm.chunk_index,
        created_at=orm.created_at,
    )