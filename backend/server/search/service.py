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
  ``/search`` always did; ``"embedding"`` is accepted as a legacy alias).
* ``keyword`` — BM25 sparse retrieval over the chunk text via
  ``ChunkRepository.search_bm25``, scoped to the selected run's chunks. No
  embedding model is used, so the query never touches Ollama/Qdrant.
* ``hybrid`` — runs both the dense and the BM25 halves and fuses their rankings
  with Reciprocal Rank Fusion (see ``reciprocal_rank_fusion``).
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from qdrant_client import QdrantClient

from backend.server.compare.embedder import get_embeddings
from backend.server.pipeline.runs import get_pipeline_run
from backend.shared import config
from backend.shared.models import Search, SearchInput
from backend.shared.storage.sql.sql_store import SqlStore
from backend.shared.storage.vector.vector_store import VectorStore

DEFAULT_TOP_K = 10

# Reciprocal Rank Fusion constant. The standard value from the original RRF
# paper (Cormack et al., 2009); it dampens the contribution of lower-ranked
# items so a single list can't dominate. Fixed rather than user-tunable.
RRF_K = 60

# Retrieval strategies accepted on the request. ``embedding`` is a legacy alias
# for ``semantic`` kept so previously-persisted/UI configs keep working; it is
# normalised to ``semantic`` before use.
_STRATEGY_ALIASES = {"embedding": "semantic"}
_VALID_STRATEGIES = {"semantic", "keyword", "hybrid"}


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


def parse_strategy(value) -> str | None:
    """Normalise the request's ``searchMethod`` to a known strategy name.

    Missing/empty falls back to ``"semantic"`` (the legacy behaviour). The
    legacy ``"embedding"`` alias maps to ``"semantic"``. Anything else that
    isn't one of ``semantic``/``keyword``/``hybrid`` yields ``None`` so the
    caller can reject the request.
    """
    if value is None or value == "":
        return "semantic"
    if not isinstance(value, str):
        return None
    normalized = _STRATEGY_ALIASES.get(value.lower().strip(), value.lower().strip())
    return normalized if normalized in _VALID_STRATEGIES else None


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]], k: int = RRF_K
) -> list[tuple[str, float]]:
    """Fuse several ranked id lists into one via Reciprocal Rank Fusion.

    Each list is an ordering of item ids, best-first. An item's fused score is
    the sum over the lists it appears in of ``1 / (k + rank)``, where ``rank``
    is its 1-based position in that list. Larger ``k`` flattens the weight
    curve (later ranks matter relatively more); the standard default is
    ``RRF_K``.

    Returns ``(item_id, fused_score)`` pairs sorted by descending fused score.
    Ties are broken by item id so the ordering is deterministic (important for
    reproducible results and tests). Items absent from every list simply do not
    appear.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


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
    store: Optional[VectorStore] = None
    model_name: Optional[str] = None
    query_embeddings: Optional[list] = None

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
        mock_dim: Optional[int] = None
        if provider_type == "mock":
            mock_dim = provider_snap.get("mock_dim", config.MOCK_EMBED_DIM)
        ollama_port = request.configuration.get("ollamaPort")

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

        query_embeddings = await get_embeddings(
            provider_type,
            model_name,
            ollama_port,
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

    results: List[dict] = []
    for index, query in enumerate(queries):
        embedding = query_embeddings[index] if query_embeddings is not None else None

        if strategy == "semantic":
            query_results = _semantic_search(
                store_sql,
                store,
                query,
                embedding,
                top_k,
                pipeline_id,
                model_name,
                dataset_name,
            )
        elif strategy == "keyword":
            query_results = _keyword_search(
                store_sql, query, top_k, run.id, dataset_name
            )
        else:  # hybrid
            query_results = _hybrid_search(
                store_sql,
                store,
                query,
                embedding,
                top_k,
                run.id,
                model_name,
                dataset_name,
            )

        results.extend(query_results)
        _persist_search(store_sql, query, run.id, query_results, top_k, strategy)

    return {"status": "success", "results": results}


def _semantic_search(
    store_sql: SqlStore,
    store: VectorStore,
    query,
    embedding: list,
    top_k: int,
    pipeline_id: str,
    model_name: Optional[str],
    dataset_name: str,
) -> List[dict]:
    """Dense nearest-neighbour retrieval for one query.

    Asks Qdrant for the nearest ``top_k`` vectors in the run's collection, then
    joins each hit back to Postgres for chunk text and document metadata. The
    score is Qdrant's similarity score (higher is better, unchanged).
    """
    hits = store.search(embedding, top_k=top_k, pipeline_id=pipeline_id)

    # One batched Postgres round-trip per query instead of one per hit.
    chunk_ids = [_as_uuid(hit.get("chunk_id")) for hit in hits if hit.get("chunk_id")]
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
    return query_results


def _keyword_search(
    store_sql: SqlStore,
    query,
    top_k: int,
    pipeline_id: uuid.UUID,
    dataset_name: str,
) -> List[dict]:
    """BM25 sparse retrieval for one query, scoped to the run's chunks.

    ``search_bm25`` already returns hydrated ``DocumentChunk`` objects (with
    ``.document``) best-first, so there's no extra Postgres round-trip here. The
    score is the raw BM25 score (a *negated* score — lower/more-negative is a
    better match; see ``search_bm25``). ``model`` is ``None`` because no
    embedding model is involved in the sparse signal.
    """
    hits = store_sql.chunks.search_bm25(
        query.text, limit=top_k, pipeline_id=pipeline_id
    )
    return [
        _result_from_chunk(query, chunk, score, None, dataset_name)
        for chunk, score in hits
    ]


def _hybrid_search(
    store_sql: SqlStore,
    store: VectorStore,
    query,
    embedding: list,
    top_k: int,
    pipeline_id: uuid.UUID,
    model_name: Optional[str],
    dataset_name: str,
) -> List[dict]:
    """Dense + BM25 retrieval fused with Reciprocal Rank Fusion for one query.

    Both halves are scoped to the same run. Each half is fetched at ``top_k``
    depth, then their *rankings* (not their raw, incomparable scores) are fused
    by chunk id via ``reciprocal_rank_fusion``, and the best ``top_k`` fused
    chunks are returned. The reported score is the fused RRF score.

    Dense hits carry chunk ids in the Qdrant payload while BM25 returns hydrated
    chunk objects; we fuse on the id strings and then hydrate the fused ids from
    Postgres in a single batched round-trip so both halves normalise into the
    same result dict.
    """
    dense_hits = store.search(embedding, top_k=top_k, pipeline_id=pipeline_id)
    sparse_hits = store_sql.chunks.search_bm25(
        query.text, limit=top_k, pipeline_id=pipeline_id
    )

    # Ranked id lists, best-first, as RRF expects.
    dense_ids = [str(hit["chunk_id"]) for hit in dense_hits if hit.get("chunk_id")]
    sparse_ids = [str(chunk.id) for chunk, _ in sparse_hits]

    fused = reciprocal_rank_fusion([dense_ids, sparse_ids])[:top_k]

    # Hydrate every fused chunk in one round-trip (mirroring the semantic path)
    # so dense-only hits — which arrive with only ids in the payload — get their
    # text and document metadata just like the BM25 hits already carry.
    fused_uuids = [_as_uuid(chunk_id) for chunk_id, _ in fused]
    chunks_by_id = {
        str(chunk.id): chunk
        for chunk in store_sql.chunks.get_many([u for u in fused_uuids if u])
    }

    query_results: List[dict] = []
    for chunk_id, fused_score in fused:
        chunk = chunks_by_id.get(chunk_id)
        if chunk is None:
            # Deleted between retrieval and hydration; keep a placeholder row so
            # the fused ordering is faithfully reflected.
            query_results.append(
                {
                    "source_id": query.id,
                    "queryText": query.text,
                    "score": fused_score,
                    "model": model_name,
                    "chunkId": chunk_id,
                    "documentId": None,
                    "chunkIndex": None,
                    "group": dataset_name,
                    "chunkText": None,
                    "sourceUrl": None,
                }
            )
            continue
        query_results.append(
            _result_from_chunk(query, chunk, fused_score, model_name, dataset_name)
        )
    return query_results


def _result_from_chunk(
    query,
    chunk,
    score,
    model: Optional[str],
    dataset_name: str,
) -> dict:
    """Normalise a hydrated ``DocumentChunk`` into a search result dict.

    Shared by the keyword and hybrid paths so both produce the exact same shape
    as the semantic path (which reads ids straight off the Qdrant payload).
    """
    document = chunk.document if chunk else None
    return {
        "source_id": query.id,
        "queryText": query.text,
        "score": score,
        "model": model,
        "chunkId": str(chunk.id) if chunk and chunk.id else None,
        "documentId": str(chunk.document_id) if chunk else None,
        "chunkIndex": chunk.chunk_index if chunk else None,
        "group": dataset_name,
        "chunkText": chunk.text if chunk else None,
        "sourceUrl": document.source_url if document else None,
    }


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
