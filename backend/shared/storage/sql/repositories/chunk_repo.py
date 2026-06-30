import uuid

from sqlalchemy import or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from backend.shared.models import DocumentChunk
from backend.shared.storage.sql.model_to_dto import _to_chunk, _to_document
from backend.shared.storage.sql.models.chunk import DocumentChunkORM



class ChunkRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save(self, chunk: DocumentChunk) -> DocumentChunk:
        with Session(self.engine) as session:
            orm_chunk = DocumentChunkORM(
                document_id=chunk.document_id,
                text=chunk.text,
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
        
    def get_neighbors(self, document_id: str, chunk_index: int) -> list[DocumentChunk]:
        with Session(self.engine) as session:
            statement = (
                select(DocumentChunkORM)
                .where(
                    DocumentChunkORM.document_id == document_id,
                    or_(
                        DocumentChunkORM.chunk_index == chunk_index - 1,
                        DocumentChunkORM.chunk_index == chunk_index + 1,
                    ),
                )
                .options(selectinload(DocumentChunkORM.document))
            )
            orm_chunks = session.scalars(statement).all()
            result: list[DocumentChunk] = []
            for orm_chunk in orm_chunks:
                chunk = _to_chunk(orm_chunk)
                if orm_chunk.document is not None:
                    chunk.document = _to_document(orm_chunk.document)
                result.append(chunk)
            return result

    def list_by_document(self, document_id: uuid.UUID) -> list[DocumentChunk]:
        with Session(self.engine) as session:
            statement = (
                select(DocumentChunkORM)
                .where(DocumentChunkORM.document_id == document_id)
                .order_by(DocumentChunkORM.chunk_index)
            )
            return [_to_chunk(orm) for orm in session.scalars(statement).all()]

    def get_many(self, chunk_ids: list[uuid.UUID]) -> list[DocumentChunk]:
        if not chunk_ids:
            return []

        with Session(self.engine) as session:
            statement = (
                select(DocumentChunkORM)
                .where(DocumentChunkORM.id.in_(chunk_ids))
                .options(selectinload(DocumentChunkORM.document))
            )

            orm_chunks = session.scalars(statement).all()

            result: list[DocumentChunk] = []

            for orm_chunk in orm_chunks:
                chunk = _to_chunk(orm_chunk)

                if orm_chunk.document is not None:
                    chunk.document = _to_document(orm_chunk.document)

                result.append(chunk)

            return result