"""Cross-encoder reranking for hybrid search.

Reranking is an optional second stage layered on top of hybrid retrieval: the
fused RRF pool is re-scored by a cross-encoder that reads each ``(query,
candidate text)`` pair jointly, then the best ``rerankerTopK`` are kept. RRF
fuses two *incomparable* rankings by position; a cross-encoder instead judges
relevance directly, so it can sharpen the top of the list at the cost of a model
load and one forward pass per candidate.

Two failure modes are handled differently, matching how ``search_db`` reports
errors elsewhere:

* **Config errors** (unknown provider id, wrong ``model_type``) are validated up
  front by :func:`resolve_reranker_target` and surface as the request's error
  body — the user asked for a specific provider that cannot rerank.
* **Runtime errors** (the reranker endpoint being unreachable or returning an
  error) degrade gracefully: :func:`rerank_results` logs and returns the
  original results (capped to ``reranker_top_k``), because a transient network
  problem must never break an otherwise-good hybrid search — mirroring
  ``_persist_search``'s best-effort pattern.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from backend.plugins.provider_types.base import ResolvedRerankTarget
from backend.plugins.provider_types.registry import resolve_rerank_target
from backend.shared.storage.sql.sql_store import SqlStore

log = logging.getLogger(__name__)


def resolve_reranker_target(
    store_sql: SqlStore, provider_id: str
) -> ResolvedRerankTarget:
    """Load the reranker provider and resolve its config into a rerank target.

    Hard-validates the request's reranker selection: the id must parse, the
    provider must exist, and its ``model_type`` must be ``cross-encoder``. Any
    of these raise ``ValueError`` so the caller can reject the request with a
    clear error body (the user picked a provider that cannot rerank).
    """
    try:
        parsed = uuid.UUID(str(provider_id))
    except (ValueError, TypeError):
        raise ValueError(f"Invalid reranker provider id: {provider_id!r}") from None

    provider = store_sql.providers.get(parsed)
    if provider is None:
        raise ValueError("Unknown reranker provider")
    if provider.model_type != "cross-encoder":
        raise ValueError(
            "Reranker provider must be a cross-encoder model, "
            f"got {provider.model_type!r}"
        )
    return resolve_rerank_target(provider.provider_type, provider.config)


async def rerank_results(
    target: ResolvedRerankTarget,
    query,
    query_results: list[dict],
    reranker_top_k: int,
) -> list[dict]:
    """Re-score *query_results* with the cross-encoder and keep the top ``k``.

    Only rows with non-empty ``chunkText`` can be scored — placeholder rows for
    chunks deleted between retrieval and hydration have no text — so they are
    excluded from the reranked output. Each surviving row's ``score`` is
    overwritten with its rerank score and the list is sorted descending.

    Best-effort: the blocking HTTP call runs off the event loop, and any failure
    is logged and degrades to the original ordering (capped to
    ``reranker_top_k``) so reranking can never break search.
    """
    scorable = [r for r in query_results if (r.get("chunkText") or "").strip()]
    if not scorable:
        return query_results[:reranker_top_k]

    try:
        client = _build_client(target)
        texts = [r["chunkText"] for r in scorable]
        scores = await asyncio.to_thread(client.rerank, query.text, texts)
    except Exception:
        log.exception(
            "Reranking failed (provider=%s model=%s base_url=%s); "
            "returning original hybrid results",
            target.provider,
            target.model,
            target.base_url,
        )
        return query_results[:reranker_top_k]

    for result, score in zip(scorable, scores):
        result["score"] = float(score)
    ranked = sorted(scorable, key=lambda r: r["score"], reverse=True)
    return ranked[:reranker_top_k]


def _build_client(target: ResolvedRerankTarget):
    """Build the rerank client for a resolved target, dispatched by provider key.

    Mirrors ``embedder.get_embeddings``' provider dispatch so adding another
    reranker backend (a mock, a different remote API) is a new branch plus its
    client, not a change to the search orchestrator. The client import is
    deferred to keep this module import-light on the non-rerank hot path.
    """
    if target.provider == "http_rerank":
        from backend.shared.clients.http_rerank_client import HttpRerankClient

        return HttpRerankClient(
            model=target.model,
            base_url=target.base_url,
            api_key=target.api_key,
            path=target.path,
        )
    raise ValueError(f"Unsupported reranker provider: {target.provider!r}")
