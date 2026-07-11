"""Reciprocal Rank Fusion (RRF).

A standalone, pure fusion primitive: it takes several ranked id lists and
combines them into a single ranking. It is its own module because it is a
reusable retrieval building block — the hybrid strategy fuses its dense and
BM25 halves with it, and it is exercised directly by the search tests.
"""

from __future__ import annotations

# Reciprocal Rank Fusion constant. The standard value from the original RRF
# paper (Cormack et al., 2009); it dampens the contribution of lower-ranked
# items so a single list can't dominate. Fixed rather than user-tunable.
RRF_K = 60


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
