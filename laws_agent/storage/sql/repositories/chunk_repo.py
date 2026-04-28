import uuid

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from laws_agent.models import DocumentChunk
from laws_agent.storage.sql.models.chunk import DocumentChunkORM
from laws_agent.storage.sql.model_to_dto import _to_chunk, _to_document

class ChunkRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save(self, chunk: DocumentChunk) -> DocumentChunk:
        with Session(self.engine) as session:
            orm_chunk = DocumentChunkORM(
                document_id=chunk.document_id,
                text=chunk.text,
                links=chunk.links,
                chunk_index=chunk.chunk_index,
            )
            session.add(orm_chunk)
            session.commit()
            session.refresh(orm_chunk)

            return _to_chunk(orm_chunk)

    def save_many(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        with Session(self.engine) as session:
            orm_chunks = [
                DocumentChunkORM(
                    document_id=chunk.document_id,
                    text=chunk.text,
                    links=chunk.links,
                    chunk_index=chunk.chunk_index,
                )
                for chunk in chunks
            ]

            session.add_all(orm_chunks)
            session.commit()

            for orm_chunk in orm_chunks:
                session.refresh(orm_chunk)

            return [_to_chunk(orm_chunk) for orm_chunk in orm_chunks]

    def get_with_document(self, chunk_id: uuid.UUID) -> DocumentChunk | None:
        with Session(self.engine) as session:
            orm_chunk = session.get(
                DocumentChunkORM,
                chunk_id,
                options=[selectinload(DocumentChunkORM.document)],
            )

            if orm_chunk is None:
                return None

            result = _to_chunk(orm_chunk)
            result.document = _to_document(orm_chunk.document)

            return result