from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.shared.models import SearchInput
from backend.shared.storage.sql.model_to_dto import _to_search_input
from backend.shared.storage.sql.models.search_input import SearchInputORM


class SearchInputRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, search_input: SearchInput) -> SearchInput:
        """Persist a new search input row and return the saved domain model."""
        with Session(self.engine) as session:
            orm = SearchInputORM(text=search_input.text)
            session.add(orm)
            session.commit()
            session.refresh(orm)
            return _to_search_input(orm)

    def get(self, search_input_id: uuid.UUID) -> Optional[SearchInput]:
        """Return the search input with *search_input_id*, or ``None``."""
        with Session(self.engine) as session:
            orm = session.get(SearchInputORM, search_input_id)
            return _to_search_input(orm) if orm else None

    def list_recent(self, limit: int = 100) -> List[SearchInput]:
        """Return search inputs ordered newest first, up to *limit* rows."""
        with Session(self.engine) as session:
            stmt = (
                select(SearchInputORM)
                .order_by(SearchInputORM.created_at.desc())
                .limit(limit)
            )
            return [_to_search_input(orm) for orm in session.scalars(stmt).all()]
