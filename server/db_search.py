"""Vector-DB search for the matcher API.

Unlike ``/compare`` (which scores the user's source texts against the user's
own candidate texts), ``/search`` treats each source text as a *query* against
a RAG collection already populated by the laws-agent ingestion pipeline.

The caller selects a *pipeline run* (``runId``) rather than a raw collection +
model: the run records both the Qdrant collection it populated and the
embedding provider/model it was built with, so we read those straight off it.
That guarantees the query is embedded with the same model the collection was
indexed with (matching dimensions), with no chance of the user mismatching them:

1. Load the run from Postgres and read its ``collection`` and embed ``model``.
2. Embed the query with that model (via Ollama).
3. Ask Qdrant for the nearest ``TOP_K`` vectors. We deliberately don't pass any
   similarity metric here — the distance is fixed at collection-creation time
   (see the run's ``vector_store.similarity``), and Qdrant ranks for us.
4. Each hit's payload carries ``chunk_id``/``document_id`` (written by the
   embed_chunks actor), so we join back to Postgres for the chunk text and its
   document metadata, returning the full "batch info" to the UI.
"""

from __future__ import annotations

import logging
import uuid
from typing import List

from embedder import get_embeddings
from laws_agent.storage.sql.sql_store import SqlStore
from laws_agent.storage.vector.vector_store import VectorStore
from pipeline_runs import get_pipeline_run

TOP_K = 10


async def search_db(request) -> dict:
    run_id = request.configuration.get("runId")
    if not run_id:
        return {"status": "error", "detail": "No pipeline run selected", "results": []}

    run = get_pipeline_run(run_id)
    if run is None:
        return {"status": "error", "detail": "Unknown pipeline run", "results": []}

    # Provider, collection and embedding model all come from the run's saved
    # launch configuration — never from user input — so a query is always
    # embedded the same way the collection was.
    collection = run.collection_name
    embed_cfg = run.settings.embed_chunks
    model_name = embed_cfg.model
    provider = embed_cfg.provider
    ollama_port = request.configuration.get("ollamaPort")

    queries = request.source.inputs
    logging.info(
        "DB search: run=%s collection=%s provider=%s model=%s queries=%d",
        run_id,
        collection,
        provider,
        model_name,
        len(queries),
    )

    query_embeddings = await get_embeddings(
        provider,
        model_name,
        ollama_port,
        [q.text for q in queries],
        mock_dim=embed_cfg.mock_dim,
    )

    store = VectorStore(collection=collection)
    store_sql = SqlStore(application_name="embedorium-search")

    results: List[dict] = []
    try:
        for query, embedding in zip(queries, query_embeddings):
            hits = store.search(embedding, top_k=TOP_K)

            # One batched Postgres round-trip per query instead of one per hit.
            chunk_ids = [
                _as_uuid(hit.get("chunk_id")) for hit in hits if hit.get("chunk_id")
            ]
            chunks_by_id = {
                str(chunk.id): chunk
                for chunk in store_sql.chunks.get_many([c for c in chunk_ids if c])
            }

            for hit in hits:
                chunk_id = hit.get("chunk_id")
                chunk = chunks_by_id.get(str(chunk_id)) if chunk_id else None
                document = chunk.document if chunk else None

                results.append(
                    {
                        "source_id": query.id,
                        "queryText": query.text,
                        "score": hit.get("score"),
                        "model": model_name,
                        "chunkId": chunk_id,
                        "documentId": hit.get("document_id"),
                        "chunkIndex": hit.get("chunk_index"),
                        "group": hit.get("group"),
                        "chunkText": chunk.text if chunk else None,
                        "sourceUrl": document.source_url if document else None,
                    }
                )
    finally:
        store_sql.close()

    return {"status": "success", "results": results}


def _as_uuid(value) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None
