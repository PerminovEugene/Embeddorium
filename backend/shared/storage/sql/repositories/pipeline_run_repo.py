from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.shared.models import PipelineRun
from backend.shared.storage.sql.model_to_dto import _to_pipeline_run
from backend.shared.storage.sql.models.pipeline_run import PipelineRunORM


class PipelineRunRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, run: PipelineRun) -> PipelineRun:
        """Persist a new pipeline run row and return the saved domain model.

        The caller must supply ``dataset`` and ``actor_configs`` dicts
        (snapshots produced by ``model_dump(mode="json")``); the provider
        snapshot lives inside ``actor_configs.embed_chunks.provider``.
        ``status`` defaults to ``"pending"`` when not set on *run*.
        """
        with Session(self.engine) as session:
            orm = PipelineRunORM(
                name=run.name,
                dataset=run.dataset,
                actor_configs=run.actor_configs,
                status=run.status,
            )
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return _to_pipeline_run(orm)

    def get(self, run_id: uuid.UUID) -> Optional[PipelineRun]:
        """Return the run with *run_id*, or ``None`` if it doesn't exist."""
        with Session(self.engine) as session:
            orm = session.get(PipelineRunORM, run_id)
            return _to_pipeline_run(orm) if orm else None

    def delete(self, run_id: uuid.UUID) -> bool:
        """Delete the run with *run_id*. Returns ``True`` if a row was deleted."""
        with Session(self.engine) as session:
            orm = session.get(PipelineRunORM, run_id)
            if orm is None:
                return False
            session.delete(orm)
            session.commit()
            return True

    def update_status(
        self,
        run_id: uuid.UUID,
        status: str,
        *,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        reset_finished: bool = False,
    ) -> Optional[PipelineRun]:
        """Advance *run_id*'s status and optionally set timestamps.

        The only mutation method: callers may not update dataset/provider/
        actor_configs after creation. Returns the updated run, or ``None``
        if the run_id is unknown.

        Parameters
        ----------
        run_id:
            UUID of the run to update.
        status:
            New lifecycle status (``"pending"``, ``"running"``,
            ``"completed"``, or ``"failed"``).
        started_at:
            When provided, sets the ``started_at`` timestamp on the row.
        finished_at:
            When provided, sets the ``finished_at`` timestamp on the row.
            Ignored when *reset_finished* is ``True``.
        reset_finished:
            When ``True``, explicitly sets ``finished_at`` to ``NULL``
            regardless of the *finished_at* argument.  Use this on relaunch
            to clear a previously-set completion timestamp so the new run
            window starts clean.
        """
        with Session(self.engine) as session:
            values: dict = {"status": status}
            if started_at is not None:
                values["started_at"] = started_at
            if reset_finished:
                values["finished_at"] = None
            elif finished_at is not None:
                values["finished_at"] = finished_at

            stmt = (
                update(PipelineRunORM)
                .where(PipelineRunORM.id == run_id)
                .values(**values)
                .returning(PipelineRunORM)
            )
            result = session.execute(stmt)
            orm = result.scalars().first()
            if orm is None:
                return None
            session.commit()
            # Refresh via a fresh get so the ORM state is clean.
            orm = session.get(PipelineRunORM, run_id)
            return _to_pipeline_run(orm) if orm else None

    def complete_if_running(
        self, run_id: uuid.UUID, finished_at: datetime
    ) -> Optional[PipelineRun]:
        """Atomically flip a running run to ``completed``.

        The ``WHERE status = 'running'`` guard makes this the idempotent
        completion primitive that ``track_pipeline_status`` relies on: both
        its triggers (``embed_chunks`` and ``schedule_discovered_links``) can
        race to detect completion for the same run, and duplicate/redelivered
        messages can call this repeatedly, but only the first caller that
        finds the row still ``running`` performs the transition — everyone
        else gets ``None`` back and treats it as a no-op.
        """
        with Session(self.engine) as session:
            stmt = (
                update(PipelineRunORM)
                .where(
                    PipelineRunORM.id == run_id,
                    PipelineRunORM.status == "running",
                )
                .values(status="completed", finished_at=finished_at)
                .returning(PipelineRunORM)
            )
            orm = session.execute(stmt).scalars().first()
            if orm is None:
                return None
            session.commit()
            orm = session.get(PipelineRunORM, run_id)
            return _to_pipeline_run(orm) if orm else None

    def list_recent(self, limit: int = 100) -> List[PipelineRun]:
        """Return pipeline runs ordered newest first, up to *limit* rows."""
        with Session(self.engine) as session:
            stmt = (
                select(PipelineRunORM)
                .order_by(PipelineRunORM.created_at.desc())
                .limit(limit)
            )
            return [_to_pipeline_run(orm) for orm in session.scalars(stmt).all()]
