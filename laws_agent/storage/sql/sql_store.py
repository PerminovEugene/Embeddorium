from __future__ import annotations

from sqlalchemy.engine import Engine

from laws_agent.storage.sql.core.engine import create_sql_engine
from laws_agent.storage.sql.core.migrations import run_migrations
from laws_agent.storage.sql.repositories.chunk_repo import ChunkRepository
from laws_agent.storage.sql.repositories.document_repo import DocumentRepository


class SqlStore:
    def __init__(self, dsn: str | None = None) -> None:
        self.engine: Engine = create_sql_engine(dsn)

        self.documents = DocumentRepository(self.engine)
        self.chunks = ChunkRepository(self.engine)

    def run_migrations(self) -> list[str]:
        return run_migrations(self.engine)

    def close(self) -> None:
        self.engine.dispose()

    def __enter__(self) -> SqlStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()