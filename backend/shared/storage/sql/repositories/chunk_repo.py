import uuid

from sqlalchemy import func, or_, select
from sqlalchemy import text as sql_text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from backend.shared.models import DocumentChunk
from backend.shared.storage.sql.model_to_dto import _to_chunk, _to_document
from backend.shared.storage.sql.models.chunk import DocumentChunkORM
from backend.shared.storage.sql.models.crawl_target import CrawlTargetORM



class ChunkRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save(self, chunk: DocumentChunk) -> DocumentChunk:
        with Session(self.engine) as session:
            orm_chunk = DocumentChunkORM(
                document_id=chunk.document_id,
                text=chunk.text,
                chunk_index=chunk.chunk_index,
            )
            session.add(orm_chunk)
            session.commit()
            session.refresh(orm_chunk)

            return _to_chunk(orm_chunk)

    def save_many(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        with Session(self.engine) as session:
            orm_chunks = [
                DocumentChunkORM(
                    document_id=chunk.document_id,
                    text=chunk.text,
                    chunk_index=chunk.chunk_index,
                )
                for chunk in chunks
            ]

            session.add_all(orm_chunks)
            session.commit()

            for orm_chunk in orm_chunks:
                session.refresh(orm_chunk)

            return [_to_chunk(orm_chunk) for orm_chunk in orm_chunks]

    def get_with_document(self, chunk_id: uuid.UUID) -> DocumentChunk | None:
        with Session(self.engine) as session:
            orm_chunk = session.get(
                DocumentChunkORM,
                chunk_id,
                options=[selectinload(DocumentChunkORM.document)],
            )

            if orm_chunk is None:
                return None

            result = _to_chunk(orm_chunk)
            result.document = _to_document(orm_chunk.document)

            return result
        
    def get_neighbors(self, document_id: str, chunk_index: int) -> list[DocumentChunk]:
        with Session(self.engine) as session:
            statement = (
                select(DocumentChunkORM)
                .where(
                    DocumentChunkORM.document_id == document_id,
                    or_(
                        DocumentChunkORM.chunk_index == chunk_index - 1,
                        DocumentChunkORM.chunk_index == chunk_index + 1,
                    ),
                )
                .options(selectinload(DocumentChunkORM.document))
            )
            orm_chunks = session.scalars(statement).all()
            result: list[DocumentChunk] = []
            for orm_chunk in orm_chunks:
                chunk = _to_chunk(orm_chunk)
                if orm_chunk.document is not None:
                    chunk.document = _to_document(orm_chunk.document)
                result.append(chunk)
            return result

    def list_by_document(self, document_id: uuid.UUID) -> list[DocumentChunk]:
        with Session(self.engine) as session:
            statement = (
                select(DocumentChunkORM)
                .where(DocumentChunkORM.document_id == document_id)
                .order_by(DocumentChunkORM.chunk_index)
            )
            return [_to_chunk(orm) for orm in session.scalars(statement).all()]

    def get_many(self, chunk_ids: list[uuid.UUID]) -> list[DocumentChunk]:
        if not chunk_ids:
            return []

        with Session(self.engine) as session:
            statement = (
                select(DocumentChunkORM)
                .where(DocumentChunkORM.id.in_(chunk_ids))
                .options(selectinload(DocumentChunkORM.document))
            )

            orm_chunks = session.scalars(statement).all()

            result: list[DocumentChunk] = []

            for orm_chunk in orm_chunks:
                chunk = _to_chunk(orm_chunk)

                if orm_chunk.document is not None:
                    chunk.document = _to_document(orm_chunk.document)

                result.append(chunk)

            return result

    def status_counts_for_pipeline(self, pipeline_id: uuid.UUID) -> dict[str, int]:
        """Aggregate chunk-status counts across every target in *pipeline_id*.

        Joins ``document_chunks`` to ``crawl_targets`` on ``document_id`` and
        groups by ``status`` in a single query, rather than maintaining a
        mutable counter column — the same "derive it from a join" approach
        ``CrawlTargetRepository.list_by_pipeline`` already uses for its
        per-target ``chunk_count``. This keeps the numbers always consistent
        with the live chunk table (no separate counter to keep in sync as
        chunks are re-chunked/re-embedded) at the cost of one aggregate query
        per read, which is cheap relative to a pipeline's write volume.

        Returns a dict keyed by ``document_chunks.status`` (e.g.
        ``{"pending": 3, "embedded": 12}``); a status with zero matching
        chunks is simply absent from the result.
        """
        stmt = (
            select(DocumentChunkORM.status, func.count(DocumentChunkORM.id))
            .join(
                CrawlTargetORM,
                CrawlTargetORM.document_id == DocumentChunkORM.document_id,
            )
            .where(CrawlTargetORM.pipeline_id == pipeline_id)
            .group_by(DocumentChunkORM.status)
        )
        with Session(self.engine) as session:
            rows = session.execute(stmt).all()
            return {status: int(count) for status, count in rows}

    def search_bm25(
        self, query: str, limit: int = 10
    ) -> list[tuple[DocumentChunk, float]]:
        """BM25 full-text search over ``document_chunks.text`` via the
        ``pg_textsearch`` extension (see migration 025 and
        https://www.pedroalonso.net/blog/postgres-bm25-search/).

        pg_textsearch adds a ``bm25`` index access method plus the ``<@>``
        operator. The operator is not modeled by the ORM (SQLAlchemy has no
        concept of it), so ranking is done with a raw, parameter-bound
        ``sqlalchemy.text()`` statement rather than ``select()`` — *never*
        string-format ``query`` into the SQL, it is bound as ``:query`` so it
        is always treated as data, not SQL.

        Importantly, ``<@>`` returns a *negated* BM25 score: lower (more
        negative) means a *better* match, which is why this method
        ``ORDER BY score ASC`` — that is the ascending order the bm25 index
        is built to serve efficiently, not a bug. Do not flip this to DESC
        without also flipping the meaning of "best".

        Implementation is two steps:
          1. Run the raw ranking query to get ``(chunk_id, score)`` pairs in
             best-first order, LIMIT-ed in the database rather than in
             Python.
          2. Hydrate those ids into full ``DocumentChunk`` domain objects via
             the ORM (``selectinload`` on ``document``, mirroring
             ``get_many``) so callers can access ``chunk.document`` — the raw
             query only ever selects ``id``/``score``, never chunk columns,
             so this stays a single source of truth for ORM -> DTO mapping
             (``_to_chunk``/``_to_document``).
        Step 2 does not preserve rank order on its own (it queries by
        ``IN (...)``), so the scores from step 1 are re-attached to the
        hydrated chunks and the result is re-sorted by score to restore the
        original BM25 ranking.

        Returns a list of ``(chunk, score)`` tuples, best match first, of at
        most ``limit`` entries (fewer if there are fewer matching rows, or if
        a matched chunk was deleted between step 1 and step 2). The raw score
        is returned rather than discarded because "lower is better" is not
        obvious to callers and a caller displaying results likely wants to
        show/compare it.
        """
        with Session(self.engine) as session:
            rank_stmt = sql_text(
                """
                SELECT id, text <@> :query AS score
                FROM document_chunks
                ORDER BY score ASC
                LIMIT :limit
                """
            )
            ranked_rows = session.execute(
                rank_stmt, {"query": query, "limit": limit}
            ).all()

            if not ranked_rows:
                return []

            score_by_id = {row.id: float(row.score) for row in ranked_rows}
            rank_order = [row.id for row in ranked_rows]

            hydrate_stmt = (
                select(DocumentChunkORM)
                .where(DocumentChunkORM.id.in_(rank_order))
                .options(selectinload(DocumentChunkORM.document))
            )
            orm_chunks_by_id = {
                orm_chunk.id: orm_chunk
                for orm_chunk in session.scalars(hydrate_stmt).all()
            }

            results: list[tuple[DocumentChunk, float]] = []
            for chunk_id in rank_order:
                orm_chunk = orm_chunks_by_id.get(chunk_id)
                if orm_chunk is None:
                    # Deleted between the ranking query and hydration; skip
                    # rather than error, the rank list is best-effort.
                    continue

                chunk = _to_chunk(orm_chunk)
                if orm_chunk.document is not None:
                    chunk.document = _to_document(orm_chunk.document)

                results.append((chunk, score_by_id[chunk_id]))

            return results