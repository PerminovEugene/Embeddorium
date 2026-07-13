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

The retrieval *strategy* is chosen per request via
``configuration["searchMethod"]``:

* ``semantic`` — the dense-vector path described above (the default, and what
  ``/search`` always did; ``"embedding"`` is accepted as a legacy alias). See
  ``service/semantic.py``.
* ``keyword`` — BM25 sparse retrieval over the chunk text via
  ``ChunkRepository.search_bm25``, scoped to the selected run's chunks. No
  embedding model is used, so the query never touches Ollama/Qdrant. See
  ``service/keyword.py``.
* ``hybrid`` — runs both the dense and the BM25 halves and fuses their rankings
  with Reciprocal Rank Fusion (see ``service/hybrid.py`` and ``service/rrf.py``).

This module is the thin orchestrator: it parses the request, loads the run,
prepares the shared dense inputs (embedding model + Qdrant store), then
dispatches each query to the selected strategy and persists the result.
"""

from __future__ import annotations

import logging
import uuid

from qdrant_client import QdrantClient

from backend.server.compare.embedder import get_embeddings
from backend.server.pipeline.runs import get_pipeline_run
from backend.server.search.service.hybrid import hybrid_search
from backend.server.search.service.keyword import keyword_search
from backend.server.search.service.params import (
    DEFAULT_TOP_K,
    parse_strategy,
    parse_top_k,
)
from backend.server.search.service.rrf import RRF_K, reciprocal_rank_fusion
from backend.server.search.service.semantic import semantic_search
from backend.shared import config
from backend.shared.models import Search, SearchInput
from backend.shared.storage.sql.sql_store import SqlStore
from backend.shared.storage.vector.vector_store import VectorStore

__all__ = [
    "DEFAULT_TOP_K",
    "RRF_K",
    "get_embeddings",
    "get_pipeline_run",
    "hybrid_search",
    "keyword_search",
    "parse_strategy",
    "parse_top_k",
    "reciprocal_rank_fusion",
    "search_db",
    "semantic_search",
]


async def search_db(store_sql: SqlStore, qdrant: QdrantClient, request) -> dict:
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

    strategy = parse_strategy(request.configuration.get("searchMethod"))
    if strategy is None:
        return {
            "status": "error",
            "detail": (
                "Unknown search strategy; expected one of semantic, keyword, hybrid"
            ),
            "results": [],
        }

    run = get_pipeline_run(store_sql, run_id)
    if run is None:
        return {"status": "error", "detail": "Unknown pipeline run", "results": []}

    # A single Qdrant collection can hold vectors from several pipeline runs, so
    # an unfiltered query would return hits from every run that ever wrote to it.
    # Each vector's payload carries the ``pipeline_id`` of the run that embedded
    # it (written by the embed_chunks actor), so we filter on the selected run's
    # id to keep results scoped to this pipeline alone. The same run id scopes
    # the BM25 half (via ``search_bm25(pipeline_id=...)``).
    pipeline_id = str(run.id)

    # Every hit necessarily belongs to the selected run's own dataset (that is
    # exactly what the pipeline_id filter above already guarantees), so the
    # dataset name is read once from the run rather than carried per-hit.
    dataset_name = run.dataset.get("name", "")

    queries = request.source.inputs

    # Only the dense strategies (semantic/hybrid) need an embedding model, the
    # Qdrant collection, and the query embeddings. The keyword path skips all of
    # that — it never touches Ollama or Qdrant.
    needs_dense = strategy in ("semantic", "hybrid")
    store: VectorStore | None = None
    model_name: str | None = None
    query_embeddings: list | None = None

    if needs_dense:
        # Provider, collection and embedding model all come from the run's saved
        # launch configuration — never from user input — so a query is always
        # embedded the same way the collection was.
        actor_cfg = run.actor_configs
        vector_store_cfg = actor_cfg.get("vector_store", {})
        # Provider snapshot lives in actor_configs.embed_chunks.provider,
        # mirroring where it was stored at run-creation time (embed_chunks is
        # the actor that uses it).
        provider_snap = actor_cfg.get("embed_chunks", {}).get("provider", {})

        collection = vector_store_cfg.get("collection", "")
        provider_type = provider_snap.get("provider_type", "")
        model_name = provider_snap.get("model_name") or provider_snap.get("model")
        # The embed_chunks actor built the collection with the same fallback:
        # when the mock provider snapshot carries no explicit dimension it uses
        # config.MOCK_EMBED_DIM. Mirror that here so the query is embedded at the
        # dimension the collection was indexed with, rather than erroring out.
        mock_dim: int | None = None
        if provider_type == "mock":
            mock_dim = provider_snap.get("mock_dim", config.MOCK_EMBED_DIM)

        logging.info(
            "DB search: run=%s strategy=%s collection=%s provider=%s model=%s "
            "pipeline=%s queries=%d top_k=%d",
            run_id,
            strategy,
            collection,
            provider_type,
            model_name,
            pipeline_id,
            len(queries),
            top_k,
        )

        # Embed the query via the pipeline's own OLLAMA_EMBED_BASE_URL — the same
        # endpoint the embed_chunks actor used to index the collection — rather
        # than an endpoint supplied on the request. This upholds the search
        # invariant: the query is embedded exactly the way the collection was.
        query_embeddings = await get_embeddings(
            provider_type,
            model_name,
            config.OLLAMA_EMBED_BASE_URL,
            [q.text for q in queries],
            mock_dim=mock_dim,
        )
        store = VectorStore(collection=collection, client=qdrant)
    else:
        logging.info(
            "DB search: run=%s strategy=%s pipeline=%s queries=%d top_k=%d",
            run_id,
            strategy,
            pipeline_id,
            len(queries),
            top_k,
        )

    results: list[dict] = []
    for index, query in enumerate(queries):
        embedding = query_embeddings[index] if query_embeddings is not None else None

        if strategy == "semantic":
            query_results = semantic_search(
                store_sql,
                store,
                query,
                embedding,
                top_k,
                pipeline_id,
                dataset_name,
            )
        elif strategy == "keyword":
            query_results = keyword_search(
                store_sql, query, top_k, pipeline_id, dataset_name
            )
        else:  # hybrid
            query_results = hybrid_search(
                store_sql,
                store,
                query,
                embedding,
                top_k,
                pipeline_id,
                dataset_name,
            )

        results.extend(query_results)
        _persist_search(store_sql, query, run.id, query_results, top_k, strategy)

    return {"status": "success", "results": results}


def _persist_search(
    store_sql: SqlStore,
    query,
    pipeline_id: uuid.UUID,
    query_results: list[dict],
    top_k: int,
    search_method: str,
) -> None:
    """Save one query launch (input text + results) to Postgres.

    ``search_method`` records the strategy actually used
    (``semantic``/``keyword``/``hybrid``) so the history endpoints report how a
    search was run.

    Best-effort: a persistence failure must never break search for the user,
    so any error is logged and swallowed.
    """
    try:
        search_input = store_sql.search_inputs.create(SearchInput(text=query.text))
        store_sql.searches.create(
            Search(
                pipeline_id=pipeline_id,
                user_input_id=search_input.id,
                search_config={"top_n": top_k, "search_method": search_method},
                results=query_results,
            )
        )
    except Exception:
        logging.exception(
            "Failed to persist search query/results for pipeline=%s", pipeline_id
        )
