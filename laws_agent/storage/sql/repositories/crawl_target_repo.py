from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from laws_agent.models.crawl_target import CrawlTarget, CrawlTargetStatus
from laws_agent.storage.sql.models.crawl_target import CrawlTargetORM


def _to_crawl_target(orm: CrawlTargetORM) -> CrawlTarget:
    return CrawlTarget(
        id=orm.id,
        group=orm.group,
        original_url=orm.original_url,
        normalized_url=orm.normalized_url,
        status=CrawlTargetStatus(orm.status),
        depth=orm.depth,
        document_id=orm.document_id,
        parent_chunk_id=orm.parent_chunk_id,
        parent_document_id=orm.parent_document_id,
        error=orm.error,
        skip_reason=orm.skip_reason,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class CrawlTargetRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save(self, target: CrawlTarget) -> CrawlTarget:
        with Session(self.engine) as session:
            orm = CrawlTargetORM(
                group=target.group,
                original_url=target.original_url,
                normalized_url=target.normalized_url,
                status=target.status,
                depth=target.depth,
                document_id=target.document_id,
                parent_chunk_id=target.parent_chunk_id,
                parent_document_id=target.parent_document_id,
                error=target.error,
                skip_reason=target.skip_reason,
            )
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return _to_crawl_target(orm)

    def save_many(self, targets: list[CrawlTarget]) -> list[CrawlTarget]:
        with Session(self.engine) as session:
            orms = [
                CrawlTargetORM(
                    group=t.group,
                    original_url=t.original_url,
                    normalized_url=t.normalized_url,
                    status=t.status,
                    depth=t.depth,
                    document_id=t.document_id,
                    parent_chunk_id=t.parent_chunk_id,
                    parent_document_id=t.parent_document_id,
                    error=t.error,
                    skip_reason=t.skip_reason,
                )
                for t in targets
            ]
            session.add_all(orms)
            session.commit()
            for orm in orms:
                session.refresh(orm)
            return [_to_crawl_target(orm) for orm in orms]

    def update_status(
        self,
        target_id: uuid.UUID,
        status: CrawlTargetStatus,
        error: Optional[str] = None,
        skip_reason: Optional[str] = None,
        document_id: Optional[uuid.UUID] = None,
    ) -> Optional[CrawlTarget]:
        with Session(self.engine) as session:
            orm = session.get(CrawlTargetORM, target_id)
            if orm is None:
                return None
            orm.status = status
            if error is not None:
                orm.error = error
            if skip_reason is not None:
                orm.skip_reason = skip_reason
            if document_id is not None:
                orm.document_id = document_id
            session.commit()
            session.refresh(orm)
            return _to_crawl_target(orm)

    def get(self, target_id: uuid.UUID) -> Optional[CrawlTarget]:
        with Session(self.engine) as session:
            orm = session.get(CrawlTargetORM, target_id)
            return _to_crawl_target(orm) if orm else None

    def find_active_by_normalized_url(
        self, group: str, normalized_url: str
    ) -> Optional[CrawlTarget]:
        """Return existing target if it exists and has not failed."""
        with Session(self.engine) as session:
            stmt = select(CrawlTargetORM).where(
                CrawlTargetORM.group == group,
                CrawlTargetORM.normalized_url == normalized_url,
                CrawlTargetORM.status != CrawlTargetStatus.FAILED,
            )
            orm = session.scalars(stmt).first()
            return _to_crawl_target(orm) if orm else None

    def get_by_normalized_url(self, normalized_url: str) -> Optional[CrawlTarget]:
        with Session(self.engine) as session:
            stmt = select(CrawlTargetORM).where(
                CrawlTargetORM.normalized_url == normalized_url
            )
            orm = session.scalars(stmt).first()
            return _to_crawl_target(orm) if orm else None

    def get_discovered(self, limit: int = 100) -> list[CrawlTarget]:
        with Session(self.engine) as session:
            stmt = (
                select(CrawlTargetORM)
                .where(CrawlTargetORM.status == CrawlTargetStatus.DISCOVERED)
                .limit(limit)
            )
            return [_to_crawl_target(orm) for orm in session.scalars(stmt).all()]
