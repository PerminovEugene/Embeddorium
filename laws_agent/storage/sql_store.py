from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    selectinload,
)
from sqlalchemy.pool import QueuePool

from laws_agent import config
from laws_agent.models import Document, DocumentChunk

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _build_dsn() -> str:
    return (
        f"postgresql+psycopg2://{config.SQL_USER}:{config.SQL_PASSWORD}"
        f"@{config.SQL_HOST}:{config.SQL_PORT}"
        f"/{config.SQL_DATABASE}"
    )


# ── ORM models ────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class DocumentORM(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    language: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sql_text("now()"),
    )

    chunks: Mapped[list["DocumentChunkORM"]] = relationship(
        "DocumentChunkORM",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="select",
    )


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


# ── converters ────────────────────────────────────────────────────────────────

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
        links=orm.links,
        chunk_index=orm.chunk_index,
        created_at=orm.created_at,
    )


# ── store ─────────────────────────────────────────────────────────────────────

class SqlStore:
    def __init__(self, dsn: str | None = None) -> None:
        self.engine = create_engine(
            dsn or _build_dsn(),
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
        )

    def run_migrations(self) -> list[str]:
        migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))

        with self.engine.begin() as conn:
            for migration_file in migration_files:
                conn.execute(sql_text(migration_file.read_text()))

        return [migration_file.name for migration_file in migration_files]

    # ── documents ─────────────────────────────────────────────────────────────

    def save_document(self, document: Document) -> Document:
        with Session(self.engine) as session:
            orm_doc = DocumentORM(
                source_url=document.source_url,
                language=document.language,
            )
            session.add(orm_doc)
            session.commit()
            session.refresh(orm_doc)

            return _to_document(orm_doc)

    def get_document(self, document_id: uuid.UUID) -> Document | None:
        with Session(self.engine) as session:
            orm_doc = session.get(DocumentORM, document_id)

            return _to_document(orm_doc) if orm_doc else None

    def get_document_with_chunks(self, document_id: uuid.UUID) -> Document | None:
        with Session(self.engine) as session:
            orm_doc = session.get(
                DocumentORM,
                document_id,
                options=[selectinload(DocumentORM.chunks)],
            )

            return _to_document(orm_doc, include_chunks=True) if orm_doc else None

    # ── chunks ────────────────────────────────────────────────────────────────

    def save_chunk(self, chunk: DocumentChunk) -> DocumentChunk:
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

    def save_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
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

    def get_chunk_with_document(self, chunk_id: uuid.UUID) -> DocumentChunk | None:
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

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        self.engine.dispose()

    def __enter__(self) -> SqlStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()