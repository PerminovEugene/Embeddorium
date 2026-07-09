"""Vector-DB search for the matcher API.

Unlike ``/compare`` (which scores the user's source texts against the user's
own candidate texts), ``/search`` treats each source text as a *query* against
a RAG collection already populated by the ingestion pipeline.

The caller selects a *pipeline run* (``runId``) rather than a raw collection +
model: the run records both the Qdrant collection it populated and the
embedding provider/model it was built with, so we read those straight off it.
That guarantees the query is embedded with the same model the collection was
indexed with (matching dimensions), with no chance of the user mismatching them:

1. Load the run from Postgres; read ``collection`` from
   ``actor_configs.vector_store`` and the embed provider snapshot from
   ``actor_configs.embed_chunks.provider``.
2. Embed the query with that model (via Ollama or mock).
3. Ask Qdrant for the nearest ``topK`` vectors (a per-request parameter,
   defaulting to ``DEFAULT_TOP_K``). The distance metric is fixed at
   collection-creation time; Qdrant ranks for us.
4. Each hit's payload carries ``chunk_id``/``document_id`` (written by the
   embed_chunks actor), so we join back to Postgres for chunk text and document
   metadata.
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from backend.server.compare.embedder import get_embeddings
from backend.server.pipeline.runs import get_pipeline_run
from backend.shared import config
from backend.shared.models import Search, SearchInput
from backend.shared.storage.sql.sql_store import SqlStore
from backend.shared.storage.vector.vector_store import VectorStore

DEFAULT_TOP_K = 10


def parse_top_k(value) -> int | None:
    """Coerce the request's ``topK`` to a positive int.

    Missing/empty falls back to ``DEFAULT_TOP_K``; anything that isn't a
    positive integer yields ``None`` so the caller can reject the request.
    """
    if value is None or value == "":
        return DEFAULT_TOP_K
    try:
        top_k = int(value)
    except (TypeError, ValueError):
        return None
    # int() truncates floats; only accept values with no fractional part
    # (JSON may deliver a whole number as e.g. 10.0).
    if top_k != float(value):
        return None
    return top_k if top_k >= 1 else None


async def search_db(request) -> dict:
    run_id = request.configuration.get("runId")
    if not run_id:
        return {"status": "error", "detail": "No pipeline run selected", "results": []}

    top_k = parse_top_k(request.configuration.get("topK"))
    if top_k is None:
        return {
            "status": "error",
            "detail": "topK must be a positive integer",
            "results": [],
        }

    run = get_pipeline_run(run_id)
    if run is None:
        return {"status": "error", "detail": "Unknown pipeline run", "results": []}

    # Provider, collection and embedding model all come from the run's saved
    # launch configuration — never from user input — so a query is always
    # embedded the same way the collection was.
    actor_cfg = run.actor_configs
    vector_store_cfg = actor_cfg.get("vector_store", {})
    # Provider snapshot lives in actor_configs.embed_chunks.provider, mirroring
    # where it was stored at run-creation time (embed_chunks is the actor that
    # uses it).
    provider_snap = actor_cfg.get("embed_chunks", {}).get("provider", {})

    collection = vector_store_cfg.get("collection", "")
    provider_type = provider_snap.get("provider_type", "")
    model_name: Optional[str] = provider_snap.get("model_name") or provider_snap.get("model")
    # The embed_chunks actor built the collection with the same fallback: when
    # the mock provider snapshot carries no explicit dimension it uses
    # config.MOCK_EMBED_DIM. Mirror that here so the query is embedded at the
    # dimension the collection was indexed with, rather than erroring out.
    mock_dim: Optional[int] = None
    if provider_type == "mock":
        mock_dim = provider_snap.get("mock_dim", config.MOCK_EMBED_DIM)
    ollama_port = request.configuration.get("ollamaPort")

    # A single Qdrant collection can hold vectors from several pipeline runs, so
    # an unfiltered query would return hits from every run that ever wrote to it.
    # Each vector's payload carries the ``pipeline_id`` of the run that embedded
    # it (written by the embed_chunks actor), so we filter on the selected run's
    # id to keep results scoped to this pipeline alone.
    pipeline_id = str(run.id)

    # Every hit necessarily belongs to the selected run's own dataset (that is
    # exactly what the pipeline_id filter above already guarantees), so the
    # dataset name is read once from the run rather than carried per-vector in
    # Qdrant.
    dataset_name = run.dataset.get("name", "")

    queries = request.source.inputs
    logging.info(
        "DB search: run=%s collection=%s provider=%s model=%s pipeline=%s queries=%d top_k=%d",
        run_id,
        collection,
        provider_type,
        model_name,
        pipeline_id,
        len(queries),
        top_k,
    )

    query_embeddings = await get_embeddings(
        provider_type,
        model_name,
        ollama_port,
        [q.text for q in queries],
        mock_dim=mock_dim,
    )

    store = VectorStore(collection=collection)
    store_sql = SqlStore(application_name="embeddorium-search")

    results: List[dict] = []
    try:
        for query, embedding in zip(queries, query_embeddings):
            hits = store.search(embedding, top_k=top_k, pipeline_id=pipeline_id)

            # One batched Postgres round-trip per query instead of one per hit.
            chunk_ids = [
                _as_uuid(hit.get("chunk_id")) for hit in hits if hit.get("chunk_id")
            ]
            chunks_by_id = {
                str(chunk.id): chunk
                for chunk in store_sql.chunks.get_many([c for c in chunk_ids if c])
            }

            query_results: List[dict] = []
            for hit in hits:
                chunk_id = hit.get("chunk_id")
                chunk = chunks_by_id.get(str(chunk_id)) if chunk_id else None
                document = chunk.document if chunk else None

                query_results.append(
                    {
                        "source_id": query.id,
                        "queryText": query.text,
                        "score": hit.get("score"),
                        "model": model_name,
                        "chunkId": chunk_id,
                        "documentId": hit.get("document_id"),
                        "chunkIndex": hit.get("chunk_index"),
                        "group": dataset_name,
                        "chunkText": chunk.text if chunk else None,
                        "sourceUrl": document.source_url if document else None,
                    }
                )

            results.extend(query_results)
            _persist_search(store_sql, query, run.id, query_results, top_k)
    finally:
        store_sql.close()

    return {"status": "success", "results": results}


def _as_uuid(value) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _persist_search(
    store_sql: SqlStore,
    query,
    pipeline_id: uuid.UUID,
    query_results: List[dict],
    top_k: int,
) -> None:
    """Save one query launch (input text + results) to Postgres.

    Best-effort: a persistence failure must never break search for the user,
    so any error is logged and swallowed.
    """
    try:
        search_input = store_sql.search_inputs.create(SearchInput(text=query.text))
        store_sql.searches.create(
            Search(
                pipeline_id=pipeline_id,
                user_input_id=search_input.id,
                search_config={"top_n": top_k, "search_method": "embedding"},
                results=query_results,
            )
        )
    except Exception:
        logging.exception(
            "Failed to persist search query/results for pipeline=%s", pipeline_id
        )
