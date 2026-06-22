import uuid

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from laws_agent.models import Document
from laws_agent.storage.sql.models.document import DocumentORM
from laws_agent.storage.sql.model_to_dto import _to_document


class DocumentRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save(self, document: Document) -> Document:
        with Session(self.engine) as session:
            orm_doc = DocumentORM(
                source_url=document.source_url,
                language=document.language,
            )
            session.add(orm_doc)
            session.commit()
            session.refresh(orm_doc)

            return _to_document(orm_doc)

    def get(self, document_id: uuid.UUID) -> Document | None:
        with Session(self.engine) as session:
            orm_doc = session.get(DocumentORM, document_id)
            return _to_document(orm_doc) if orm_doc else None

    def get_by_crawl_target(self, crawl_target_id: uuid.UUID) -> Document | None:
        with Session(self.engine) as session:
            orm_doc = session.scalars(
                select(DocumentORM).where(
                    DocumentORM.crawl_target_id == crawl_target_id
                )
            ).first()
            return _to_document(orm_doc) if orm_doc else None

    def get_with_chunks(self, document_id: uuid.UUID) -> Document | None:
        with Session(self.engine) as session:
            orm_doc = session.get(
                DocumentORM,
                document_id,
                options=[selectinload(DocumentORM.chunks)],
            )

            return _to_document(orm_doc, include_chunks=True) if orm_doc else None