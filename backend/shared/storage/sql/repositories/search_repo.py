from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.shared.models import Search
from backend.shared.storage.sql.model_to_dto import _to_search
from backend.shared.storage.sql.models.search import SearchORM


class SearchRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, search: Search) -> Search:
        """Persist a new search row and return the saved domain model."""
        with Session(self.engine) as session:
            orm = SearchORM(
                pipeline_id=search.pipeline_id,
                user_input_id=search.user_input_id,
                search_config=search.search_config,
                results=search.results,
            )
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return _to_search(orm)

    def get(self, search_id: uuid.UUID) -> Optional[Search]:
        """Return the search with *search_id*, or ``None`` if it doesn't exist."""
        with Session(self.engine) as session:
            orm = session.get(SearchORM, search_id)
            return _to_search(orm) if orm else None

    def list_recent(self, limit: int = 100) -> List[Search]:
        """Return searches ordered newest first, up to *limit* rows."""
        with Session(self.engine) as session:
            stmt = (
                select(SearchORM)
                .order_by(SearchORM.created_at.desc())
                .limit(limit)
            )
            return [_to_search(orm) for orm in session.scalars(stmt).all()]

    def delete(self, search_id: uuid.UUID) -> bool:
        """Delete the search with *search_id*. Returns ``True`` if a row was
        deleted."""
        with Session(self.engine) as session:
            orm = session.get(SearchORM, search_id)
            if orm is None:
                return False
            session.delete(orm)
            session.commit()
            return True
