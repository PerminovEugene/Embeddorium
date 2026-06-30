from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.shared.models import Dataset
from backend.shared.storage.sql.model_to_dto import _to_dataset
from backend.shared.storage.sql.models.dataset import DatasetORM


class DatasetRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, dataset: Dataset) -> Dataset:
        with Session(self.engine) as session:
            orm = DatasetORM(
                name=dataset.name,
                source_type=dataset.source_type,
                url=getattr(dataset, "url", None),
                process_child_links=getattr(dataset, "process_child_links", None),
                process_cross_domain_links=getattr(
                    dataset, "process_cross_domain_links", None
                ),
                depth=getattr(dataset, "depth", None),
                paths=getattr(dataset, "paths", None),
            )
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return _to_dataset(orm)

    def get(self, dataset_id: uuid.UUID) -> Optional[Dataset]:
        with Session(self.engine) as session:
            orm = session.get(DatasetORM, dataset_id)
            return _to_dataset(orm) if orm else None

    def list_recent(self, limit: int = 100) -> list[Dataset]:
        with Session(self.engine) as session:
            stmt = (
                select(DatasetORM)
                .order_by(DatasetORM.created_at.desc())
                .limit(limit)
            )
            return [_to_dataset(orm) for orm in session.scalars(stmt).all()]

    def update(self, dataset_id: uuid.UUID, dataset: Dataset) -> Optional[Dataset]:
        with Session(self.engine) as session:
            orm = session.get(DatasetORM, dataset_id)
            if orm is None:
                return None
            orm.name = dataset.name
            orm.source_type = dataset.source_type
            orm.url = getattr(dataset, "url", None)
            orm.process_child_links = getattr(dataset, "process_child_links", None)
            orm.process_cross_domain_links = getattr(
                dataset, "process_cross_domain_links", None
            )
            orm.depth = getattr(dataset, "depth", None)
            orm.paths = getattr(dataset, "paths", None)
            session.commit()
            session.refresh(orm)
            return _to_dataset(orm)

    def delete(self, dataset_id: uuid.UUID) -> bool:
        with Session(self.engine) as session:
            orm = session.get(DatasetORM, dataset_id)
            if orm is None:
                return False
            session.delete(orm)
            session.commit()
            return True
