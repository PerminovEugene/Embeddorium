from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from laws_agent.models import PipelineRun
from laws_agent.storage.sql.model_to_dto import _to_pipeline_run
from laws_agent.storage.sql.models.pipeline_run import PipelineRunORM


class PipelineRunRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def ensure_for_group(self, run: PipelineRun) -> PipelineRun:
        """Record *run*'s launch config for its group, once, at pipeline start.

        Idempotent and race-safe via the unique index on ``group`` (ON CONFLICT
        DO NOTHING): the first entry-actor message of a run inserts the row;
        every later message for the same group (discovered links looping back,
        sibling XML files) is a cheap no-op. Returns the row that exists for the
        group afterwards — freshly inserted or pre-existing.
        """
        with Session(self.engine) as session:
            stmt = (
                pg_insert(PipelineRunORM)
                .values(
                    group=run.group,
                    source_type=run.source_type,
                    collection_name=run.collection_name,
                    settings=run.settings.model_dump(),
                )
                .on_conflict_do_nothing(index_elements=[PipelineRunORM.group])
            )
            session.execute(stmt)
            session.commit()
            orm = session.scalar(
                select(PipelineRunORM).where(PipelineRunORM.group == run.group)
            )
            return _to_pipeline_run(orm)

    def create(self, run: PipelineRun) -> PipelineRun:
        with Session(self.engine) as session:
            orm = PipelineRunORM(
                group=run.group,
                source_type=run.source_type,
                collection_name=run.collection_name,
                settings=run.settings.model_dump(),
            )
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return _to_pipeline_run(orm)

    def get(self, run_id: uuid.UUID) -> Optional[PipelineRun]:
        with Session(self.engine) as session:
            orm = session.get(PipelineRunORM, run_id)
            return _to_pipeline_run(orm) if orm else None

    def get_by_group(self, group: str) -> Optional[PipelineRun]:
        """Return the run recorded for *group* (one row per group), or None.

        Used by the chunk/embed stages to read the launch config their run was
        started with, instead of re-reading global env config per message.
        """
        with Session(self.engine) as session:
            orm = session.scalar(
                select(PipelineRunORM).where(PipelineRunORM.group == group)
            )
            return _to_pipeline_run(orm) if orm else None

    def list_recent(
        self, group: Optional[str] = None, limit: int = 100
    ) -> list[PipelineRun]:
        with Session(self.engine) as session:
            stmt = select(PipelineRunORM).order_by(PipelineRunORM.created_at.desc())
            if group is not None:
                stmt = stmt.where(PipelineRunORM.group == group)
            stmt = stmt.limit(limit)
            return [_to_pipeline_run(orm) for orm in session.scalars(stmt).all()]
