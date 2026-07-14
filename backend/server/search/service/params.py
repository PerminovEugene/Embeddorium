"""Request-parameter parsing for ``/search``.

Small, pure validators for the two per-request knobs that the ``/search``
handler reads out of the untyped ``configuration`` dict: ``topK`` (result count)
and ``searchMethod`` (retrieval strategy). Both return ``None`` on invalid
input so the orchestrator can reject the request with a 4xx-style error body.
"""

from __future__ import annotations

DEFAULT_TOP_K = 10

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


def parse_reranker_top_k(value) -> int | None:
    """Coerce the request's ``rerankerTopK`` to a positive int.

    Unlike :func:`parse_top_k` there is no default: reranking is opt-in, so when
    ``useReranking`` is set the count must be given explicitly. Missing/empty or
    a non-positive-integer value yields ``None`` so the caller can reject the
    request.
    """
    if value is None or value == "":
        return None
    try:
        top_k = int(value)
    except (TypeError, ValueError):
        return None
    # int() truncates floats; only accept whole numbers (JSON may send 5.0).
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
