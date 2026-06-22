import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from laws_agent.models import OutboxEvent, OutboxStatus
from laws_agent.storage.sql.model_to_dto import _to_outbox_event
from laws_agent.storage.sql.models.outbox_event import OutboxEventORM


class OutboxRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_pending(self, limit: int = 100) -> list[OutboxEvent]:
        with Session(self.engine) as session:
            stmt = (
                select(OutboxEventORM)
                .where(OutboxEventORM.status == OutboxStatus.PENDING)
                .order_by(OutboxEventORM.created_at)
                .limit(limit)
            )
            return [_to_outbox_event(orm) for orm in session.scalars(stmt).all()]

    def mark_sent(self, event_id: uuid.UUID) -> None:
        with Session(self.engine) as session:
            session.execute(
                update(OutboxEventORM)
                .where(OutboxEventORM.id == event_id)
                .values(status=OutboxStatus.SENT, sent_at=datetime.now(timezone.utc))
            )
            session.commit()

    def record_attempt(self, event_id: uuid.UUID) -> None:
        """Increment the attempt counter (used when a publish fails)."""
        with Session(self.engine) as session:
            session.execute(
                update(OutboxEventORM)
                .where(OutboxEventORM.id == event_id)
                .values(attempts=OutboxEventORM.attempts + 1)
            )
            session.commit()
