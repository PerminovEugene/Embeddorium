from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.shared.models import Provider
from backend.shared.storage.sql.model_to_dto import _to_provider
from backend.shared.storage.sql.models.provider import ProviderORM


class ProviderRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, provider: Provider) -> Provider:
        with Session(self.engine) as session:
            orm = ProviderORM(
                name=provider.name,
                provider_type=provider.provider_type,
                model_type=provider.model_type,
                config=dict(provider.config or {}),
            )
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return _to_provider(orm)

    def get(self, provider_id: uuid.UUID) -> Optional[Provider]:
        with Session(self.engine) as session:
            orm = session.get(ProviderORM, provider_id)
            return _to_provider(orm) if orm else None

    def list_recent(self, limit: int = 100) -> list[Provider]:
        with Session(self.engine) as session:
            stmt = (
                select(ProviderORM)
                .order_by(ProviderORM.created_at.desc())
                .limit(limit)
            )
            return [_to_provider(orm) for orm in session.scalars(stmt).all()]

    def update(
        self, provider_id: uuid.UUID, provider: Provider
    ) -> Optional[Provider]:
        with Session(self.engine) as session:
            orm = session.get(ProviderORM, provider_id)
            if orm is None:
                return None
            orm.name = provider.name
            orm.provider_type = provider.provider_type
            orm.model_type = provider.model_type
            orm.config = dict(provider.config or {})
            session.commit()
            session.refresh(orm)
            return _to_provider(orm)

    def delete(self, provider_id: uuid.UUID) -> bool:
        with Session(self.engine) as session:
            orm = session.get(ProviderORM, provider_id)
            if orm is None:
                return False
            session.delete(orm)
            session.commit()
            return True
