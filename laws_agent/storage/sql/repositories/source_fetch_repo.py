import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from laws_agent.models import SourceFetch
from laws_agent.storage.sql.model_to_dto import _to_source_fetch
from laws_agent.storage.sql.models.source_fetch import SourceFetchORM


class SourceFetchRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_by_crawl_target(self, crawl_target_id: uuid.UUID) -> Optional[SourceFetch]:
        with Session(self.engine) as session:
            orm = session.scalars(
                select(SourceFetchORM).where(
                    SourceFetchORM.crawl_target_id == crawl_target_id
                )
            ).first()
            return _to_source_fetch(orm) if orm else None
