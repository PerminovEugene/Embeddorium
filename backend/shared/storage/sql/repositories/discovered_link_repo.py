import uuid

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.shared.models import DiscoveredLink, DiscoveredLinkStatus
from backend.shared.storage.sql.model_to_dto import _to_discovered_link
from backend.shared.storage.sql.models.discovered_link import DiscoveredLinkORM


class DiscoveredLinkRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_pending_by_document(
        self, source_document_id: uuid.UUID
    ) -> list[DiscoveredLink]:
        with Session(self.engine) as session:
            stmt = select(DiscoveredLinkORM).where(
                DiscoveredLinkORM.source_document_id == source_document_id,
                DiscoveredLinkORM.status == DiscoveredLinkStatus.PENDING,
            )
            return [_to_discovered_link(orm) for orm in session.scalars(stmt).all()]
