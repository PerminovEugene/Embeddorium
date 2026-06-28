from __future__ import annotations

from sqlalchemy.engine import Engine

from laws_agent.storage.sql.core.engine import SqlPoolConfig, create_sql_engine
from laws_agent.storage.sql.core.migrations import run_migrations
from laws_agent.storage.sql.repositories.chunk_repo import ChunkRepository
from laws_agent.storage.sql.repositories.crawl_target_repo import CrawlTargetRepository
from laws_agent.storage.sql.repositories.discovered_link_repo import (
    DiscoveredLinkRepository,
)
from laws_agent.storage.sql.repositories.document_repo import DocumentRepository
from laws_agent.storage.sql.repositories.outbox_repo import OutboxRepository
from laws_agent.storage.sql.repositories.pipeline_run_repo import (
    PipelineRunRepository,
)
from laws_agent.storage.sql.repositories.source_fetch_repo import SourceFetchRepository
from laws_agent.storage.sql.unit_of_work import UnitOfWork


class SqlStore:
    def __init__(
        self,
        dsn: str | None = None,
        *,
        pool_config: SqlPoolConfig | None = None,
        application_name: str | None = None,
    ) -> None:
        self.engine: Engine = create_sql_engine(
            dsn, pool_config=pool_config, application_name=application_name
        )

        self.documents = DocumentRepository(self.engine)
        self.chunks = ChunkRepository(self.engine)
        self.crawl_targets = CrawlTargetRepository(self.engine)
        self.source_fetches = SourceFetchRepository(self.engine)
        self.discovered_links = DiscoveredLinkRepository(self.engine)
        self.outbox = OutboxRepository(self.engine)
        self.pipeline_runs = PipelineRunRepository(self.engine)

    def unit_of_work(self) -> UnitOfWork:
        """Open a single-transaction unit of work for atomic multi-table writes
        (domain rows + outbox events)."""
        return UnitOfWork(self.engine)

    def run_migrations(self) -> list[str]:
        return run_migrations(self.engine)

    def close(self) -> None:
        self.engine.dispose()

    def __enter__(self) -> SqlStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
