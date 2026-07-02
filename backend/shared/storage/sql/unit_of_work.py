"""A small, explicit transactional unit of work.

Each pipeline stage performs its domain writes **and** the outbox event(s) that
trigger the next stage inside a single ``with store.unit_of_work() as uow:``
block, committed once on exit. This is what makes the DB-write + enqueue pair
atomic (no dual-write problem): the outbox dispatcher publishes events only
after they are durably committed alongside the data that produced them.

Writes are idempotent: domain rows upsert on their natural keys and outbox
events ignore conflicts on ``dedup_key``, so a retried stage is a no-op rather
than a source of duplicates.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.shared.models import (
    CrawlTargetStatus,
    DiscoveredLink,
    Document,
    DocumentChunk,
    OutboxEvent,
    SourceFetch,
)
from backend.shared.storage.sql.model_to_dto import (
    _to_chunk,
    _to_discovered_link,
    _to_document,
    _to_source_fetch,
)
from backend.shared.storage.sql.models.chunk import DocumentChunkORM
from backend.shared.storage.sql.models.crawl_target import CrawlTargetORM
from backend.shared.storage.sql.models.discovered_link import DiscoveredLinkORM
from backend.shared.storage.sql.models.document import DocumentORM
from backend.shared.storage.sql.models.outbox_event import OutboxEventORM
from backend.shared.storage.sql.models.pipeline_run import PipelineRunORM
from backend.shared.storage.sql.models.source_fetch import SourceFetchORM


class UnitOfWork:
    def __init__(self, engine: Engine) -> None:
        self._session = Session(engine)

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                self._session.commit()
            else:
                self._session.rollback()
        finally:
            self._session.close()

    # --- crawl target ---------------------------------------------------

    def set_status(
        self,
        target_id: uuid.UUID,
        status: CrawlTargetStatus,
        *,
        error: Optional[str] = None,
        skip_reason: Optional[str] = None,
        document_id: Optional[uuid.UUID] = None,
    ) -> None:
        values: dict = {"status": status}
        if error is not None:
            values["error"] = error
        if skip_reason is not None:
            values["skip_reason"] = skip_reason
        if document_id is not None:
            values["document_id"] = document_id
        self._session.execute(
            update(CrawlTargetORM)
            .where(CrawlTargetORM.id == target_id)
            .values(**values)
        )

    # --- source fetch ---------------------------------------------------

    def upsert_source_fetch(self, fetch: SourceFetch) -> SourceFetch:
        orm = (
            self._session.query(SourceFetchORM)
            .filter(SourceFetchORM.crawl_target_id == fetch.crawl_target_id)
            .one_or_none()
        )
        if orm is None:
            orm = SourceFetchORM(crawl_target_id=fetch.crawl_target_id)
            self._session.add(orm)
        orm.final_url = fetch.final_url
        orm.http_status = fetch.http_status
        orm.content_type = fetch.content_type
        orm.content_hash = fetch.content_hash
        orm.raw_content_path = fetch.raw_content_path
        orm.redirect_chain = list(fetch.redirect_chain)
        self._session.flush()
        return _to_source_fetch(orm)

    # --- document -------------------------------------------------------

    def upsert_document(self, document: Document) -> Document:
        orm: Optional[DocumentORM] = None
        if document.crawl_target_id is not None:
            orm = (
                self._session.query(DocumentORM)
                .filter(DocumentORM.crawl_target_id == document.crawl_target_id)
                .one_or_none()
            )
        if orm is None:
            orm = DocumentORM(source_url=document.source_url)
            self._session.add(orm)

        orm.source_url = document.source_url
        orm.language = document.language
        orm.group = document.group
        orm.crawl_target_id = document.crawl_target_id
        orm.normalized_url = document.normalized_url
        orm.final_url = document.final_url
        orm.http_status = document.http_status
        orm.content_type = document.content_type
        orm.content_hash = document.content_hash
        orm.text_hash = document.text_hash
        orm.parser_version = document.parser_version
        orm.chunker_version = document.chunker_version
        orm.retrieved_at = document.retrieved_at
        orm.text_path = document.text_path
        self._session.flush()
        return _to_document(orm)

    # --- chunks ---------------------------------------------------------

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        if not chunks:
            return []
        rows = [
            {
                "document_id": c.document_id,
                "text": c.text,
                "chunk_index": c.chunk_index,
                "chunk_type": c.chunk_type,
                "chunk_metadata": c.chunk_metadata,
            }
            for c in chunks
        ]
        stmt = pg_insert(DocumentChunkORM).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                DocumentChunkORM.document_id,
                DocumentChunkORM.chunk_index,
            ],
            set_={
                "text": stmt.excluded.text,
                "chunk_type": stmt.excluded.chunk_type,
                "chunk_metadata": stmt.excluded.chunk_metadata,
            },
        ).returning(DocumentChunkORM)
        orms = (
            self._session.scalars(
                stmt, execution_options={"populate_existing": True}
            )
            .all()
        )
        result = [_to_chunk(orm) for orm in orms]
        result.sort(key=lambda c: c.chunk_index)
        return result

    # --- discovered links ----------------------------------------------

    def upsert_discovered_links(
        self, links: list[DiscoveredLink]
    ) -> list[DiscoveredLink]:
        if not links:
            return []
        # Postgres rejects ON CONFLICT DO UPDATE when the same conflict key
        # appears twice in one statement. URLs that differ only by fragment
        # normalize to the same value, so collapse duplicate
        # (source_chunk_id, normalized_url) pairs, keeping the first.
        deduped: dict[tuple, DiscoveredLink] = {}
        for link in links:
            deduped.setdefault((link.source_chunk_id, link.normalized_url), link)
        rows = [
            {
                "source_document_id": link.source_document_id,
                "source_chunk_id": link.source_chunk_id,
                "raw_url": link.raw_url,
                "normalized_url": link.normalized_url,
                "anchor_text": link.anchor_text,
                "context_text": link.context_text,
                "group": link.group,
                "status": str(link.status),
            }
            for link in deduped.values()
        ]
        stmt = pg_insert(DiscoveredLinkORM).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                DiscoveredLinkORM.source_chunk_id,
                DiscoveredLinkORM.normalized_url,
            ],
            set_={"raw_url": stmt.excluded.raw_url},
        ).returning(DiscoveredLinkORM)
        orms = (
            self._session.scalars(
                stmt, execution_options={"populate_existing": True}
            )
            .all()
        )
        return [_to_discovered_link(orm) for orm in orms]

    def mark_links_scheduled(self, link_ids: list[uuid.UUID]) -> None:
        if not link_ids:
            return
        self._session.execute(
            update(DiscoveredLinkORM)
            .where(DiscoveredLinkORM.id.in_(link_ids))
            .values(status="scheduled")
        )

    # --- outbox ---------------------------------------------------------

    def add_outbox(self, event: OutboxEvent) -> bool:
        """Insert an outbox event, ignoring duplicates on ``dedup_key``.

        Returns ``True`` iff a row was actually inserted (i.e. this call was
        the first to use *event*'s ``dedup_key``) and ``False`` when it
        conflicted with an existing row. Most callers ignore the return
        value, but it is what makes the ``embeddings_scheduled`` /
        ``embeddings_completed`` counters exactly-once under at-least-once
        redelivery: a caller increments a counter only when the outbox event
        backing that increment was newly inserted, so a re-delivered message
        that finds its event already present skips the increment too.
        """
        stmt = (
            pg_insert(OutboxEventORM)
            .values(
                queue_name=event.queue_name,
                actor_name=event.actor_name,
                payload=event.payload,
                dedup_key=event.dedup_key,
            )
            .on_conflict_do_nothing(index_elements=[OutboxEventORM.dedup_key])
            .returning(OutboxEventORM.id)
        )
        inserted_id = self._session.execute(stmt).scalar()
        return inserted_id is not None

    # --- pipeline run counters -------------------------------------------

    def increment_embeddings_scheduled(self, pipeline_id: uuid.UUID, n: int) -> None:
        """Add *n* newly-scheduled embed batches to the run's counter.

        No-op when ``n <= 0`` so callers can call this unconditionally after
        counting how many outbox events were newly inserted in a batch.
        """
        if n <= 0:
            return
        self._session.execute(
            update(PipelineRunORM)
            .where(PipelineRunORM.id == pipeline_id)
            .values(embeddings_scheduled=PipelineRunORM.embeddings_scheduled + n)
        )

    def increment_embeddings_completed(self, pipeline_id: uuid.UUID, n: int) -> None:
        """Add *n* newly-completed embed batches to the run's counter.

        Mirrors :meth:`increment_embeddings_scheduled`; see that method's
        docstring and the module docstring for why this must only be called
        for outbox events that were newly inserted.
        """
        if n <= 0:
            return
        self._session.execute(
            update(PipelineRunORM)
            .where(PipelineRunORM.id == pipeline_id)
            .values(embeddings_completed=PipelineRunORM.embeddings_completed + n)
        )
