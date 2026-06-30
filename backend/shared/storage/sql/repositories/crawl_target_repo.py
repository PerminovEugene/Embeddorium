from __future__ import annotations

import uuid
from typing import Iterable, Optional

from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.shared.models.crawl_target import (
    CrawlTarget,
    CrawlTargetStatus,
    TERMINAL_OR_ACTIVE_STATUSES,
)
from backend.shared.storage.sql.models.crawl_target import CrawlTargetORM


def _to_crawl_target(orm: CrawlTargetORM) -> CrawlTarget:
    return CrawlTarget(
        id=orm.id,
        group=orm.group,
        pipeline_id=orm.pipeline_id,
        original_url=orm.original_url,
        normalized_url=orm.normalized_url,
        status=CrawlTargetStatus(orm.status),
        depth=orm.depth,
        document_id=orm.document_id,
        parent_chunk_id=orm.parent_chunk_id,
        parent_document_id=orm.parent_document_id,
        log_dir=orm.log_dir,
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
                pipeline_id=target.pipeline_id,
                original_url=target.original_url,
                normalized_url=target.normalized_url,
                status=target.status,
                depth=target.depth,
                document_id=target.document_id,
                parent_chunk_id=target.parent_chunk_id,
                parent_document_id=target.parent_document_id,
                log_dir=target.log_dir,
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
                    pipeline_id=t.pipeline_id,
                    original_url=t.original_url,
                    normalized_url=t.normalized_url,
                    status=t.status,
                    depth=t.depth,
                    document_id=t.document_id,
                    parent_chunk_id=t.parent_chunk_id,
                    parent_document_id=t.parent_document_id,
                    log_dir=t.log_dir,
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

    def acquire(
        self,
        *,
        target_id: uuid.UUID,
        from_statuses: Iterable[CrawlTargetStatus],
        to_status: CrawlTargetStatus,
    ) -> Optional[CrawlTarget]:
        """Conditional ``status`` transition used as a processing lock.

        Atomically moves the target to ``to_status`` only if its current status
        is one of ``from_statuses``. Returns the updated target if this caller
        won the transition, or ``None`` if the row was already taken/advanced by
        someone else (caller should then skip).
        """
        froms = [str(s) for s in from_statuses]
        with Session(self.engine) as session:
            stmt = (
                update(CrawlTargetORM)
                .where(
                    CrawlTargetORM.id == target_id,
                    CrawlTargetORM.status.in_(froms),
                )
                .values(status=to_status)
                .returning(CrawlTargetORM)
            )
            orm = session.execute(stmt).scalars().first()
            target = _to_crawl_target(orm) if orm else None
            session.commit()
            return target

    def get(self, target_id: uuid.UUID) -> Optional[CrawlTarget]:
        with Session(self.engine) as session:
            orm = session.get(CrawlTargetORM, target_id)
            return _to_crawl_target(orm) if orm else None

    def get_by_document_id(self, document_id: uuid.UUID) -> Optional[CrawlTarget]:
        with Session(self.engine) as session:
            stmt = select(CrawlTargetORM).where(
                CrawlTargetORM.document_id == document_id
            )
            orm = session.scalars(stmt).first()
            return _to_crawl_target(orm) if orm else None

    def find_active_by_normalized_url(
        self,
        group: str,
        normalized_url: str,
        *,
        pipeline_id: Optional[uuid.UUID] = None,
    ) -> Optional[CrawlTarget]:
        """Return an existing active target for this (pipeline, URL) pair, or None.

        Dedup is scoped to ``pipeline_id`` so that different pipeline runs may
        re-process the same source URL independently.  Within a single run the
        same source is still processed only once.

        Transient failures (and the legacy ``FAILED``) are treated as
        re-queueable, so they are excluded; everything else (including permanent
        failures and skips) counts as "active" and blocks re-queueing.

        A NULL ``pipeline_id`` (legacy rows) will never match a call that
        supplies a non-None ``pipeline_id``, so old rows never block new runs.
        """
        active = [str(s) for s in TERMINAL_OR_ACTIVE_STATUSES]
        with Session(self.engine) as session:
            stmt = select(CrawlTargetORM).where(
                CrawlTargetORM.group == group,
                CrawlTargetORM.pipeline_id == pipeline_id,
                CrawlTargetORM.normalized_url == normalized_url,
                CrawlTargetORM.status.in_(active),
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
