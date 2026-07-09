from __future__ import annotations

from sqlalchemy.engine import Engine

from backend.shared.storage.sql.core.engine import SqlPoolConfig, create_sql_engine
from backend.shared.storage.sql.core.migrations import run_migrations
from backend.shared.storage.sql.repositories.chunk_repo import ChunkRepository
from backend.shared.storage.sql.repositories.crawl_target_repo import CrawlTargetRepository
from backend.shared.storage.sql.repositories.dataset_repo import DatasetRepository
from backend.shared.storage.sql.repositories.discovered_link_repo import (
    DiscoveredLinkRepository,
)
from backend.shared.storage.sql.repositories.document_repo import DocumentRepository
from backend.shared.storage.sql.repositories.outbox_repo import OutboxRepository
from backend.shared.storage.sql.repositories.pipeline_run_repo import (
    PipelineRunRepository,
)
from backend.shared.storage.sql.repositories.provider_repo import ProviderRepository
from backend.shared.storage.sql.repositories.search_input_repo import (
    SearchInputRepository,
)
from backend.shared.storage.sql.repositories.search_repo import SearchRepository
from backend.shared.storage.sql.repositories.source_fetch_repo import SourceFetchRepository
from backend.shared.storage.sql.unit_of_work import UnitOfWork


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
        self.datasets = DatasetRepository(self.engine)
        self.providers = ProviderRepository(self.engine)
        self.search_inputs = SearchInputRepository(self.engine)
        self.searches = SearchRepository(self.engine)

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
