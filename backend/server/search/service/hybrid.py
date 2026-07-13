"""Hybrid retrieval strategy for one query.

Runs both the dense (Qdrant) and BM25 (Postgres) halves and fuses their
*rankings* — not their raw, incomparable scores — with Reciprocal Rank Fusion
(see ``rrf.reciprocal_rank_fusion``).
"""

from __future__ import annotations

from backend.server.search.service.results import as_uuid, result_from_chunk
from backend.server.search.service.rrf import reciprocal_rank_fusion
from backend.shared.storage.sql.sql_store import SqlStore
from backend.shared.storage.vector.vector_store import VectorStore


def hybrid_search(
    store_sql: SqlStore,
    store: VectorStore,
    query,
    embedding: list,
    top_k: int,
    pipeline_id: str,
    dataset_name: str,
) -> list[dict]:
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
    fused_uuids = [as_uuid(chunk_id) for chunk_id, _ in fused]
    chunks_by_id = {
        str(chunk.id): chunk
        for chunk in store_sql.chunks.get_many([u for u in fused_uuids if u])
    }

    query_results: list[dict] = []
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
                    "chunkId": chunk_id,
                    "documentId": None,
                    "chunkIndex": None,
                    "group": dataset_name,
                    "chunkText": None,
                    "sourceUrl": None,
                }
            )
            continue
        query_results.append(result_from_chunk(query, chunk, fused_score, dataset_name))
    return query_results
