"""HTTP reranker client for a vLLM (or Jina/Cohere-style) rerank server.

Talks to a reranker model hosted behind an OpenAI/Jina/Cohere-compatible rerank
endpoint over HTTP — no local model load, no torch — so it is safe to call from
the dockerized backend, mirroring how ``OllamaEmbedClient`` reaches the embedding
model. This is the networked counterpart of the embed clients; additional
reranker clients (a mock, another remote API) can be added as siblings and
dispatched on the resolved target's ``provider`` key, exactly like the embedding
side.

The canonical scoring backend is a **vLLM** server, which exposes
``POST /v1/rerank`` with the Jina/Cohere payload ``{"model", "query",
"documents"}`` and answers with ``{"results": [{"index", "relevance_score"},
...]}``. TEI, Infinity and Cohere/Jina speak the same shape. The endpoint path
and the score fields are isolated as constants below so a different server
contract is a one-line change.
"""

from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)

# The rerank endpoint path, relative to the server base URL, when a caller does
# not pass one. Servers disagree (vLLM ``v1/rerank``, Infinity ``rerank``) so the
# path is normally supplied per-provider; this is only the fallback default.
_DEFAULT_RERANK_PATH = "v1/rerank"
# The response fields carrying each candidate's original position and its score.
_INDEX_FIELD = "index"
# Different rerank servers name the score differently; accept the common ones.
_SCORE_FIELDS = ("relevance_score", "score")

# The reranker can be slow on a cold model load, so allow a generous read
# timeout while still failing rather than hanging forever.
_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


class HttpRerankClient:
    """Adapts a Jina/Cohere-style rerank endpoint to a small ``rerank`` API.

    ``rerank`` is a blocking HTTP call — callers on the async search path run it
    off the event loop via ``asyncio.to_thread``, mirroring how
    ``embedder.get_embeddings`` offloads its blocking encode.
    """

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str | None = None,
        path: str | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("HTTP reranker requires a base_url")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.path = (path or _DEFAULT_RERANK_PATH).lstrip("/")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(
            base_url=f"{self.base_url}/",
            headers=headers,
            timeout=_TIMEOUT,
        )

    @staticmethod
    def _extract_score(item: dict) -> float:
        for field in _SCORE_FIELDS:
            if field in item:
                return float(item[field])
        raise ValueError(
            f"Rerank result missing a score field (looked for {_SCORE_FIELDS}): {item}"
        )

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        """Score each candidate in *texts* against *query*.

        Sends the whole candidate set in a single request and returns one score
        per text, positionally aligned with the input list (the server may
        return results sorted by score, so they are re-ordered back onto the
        input positions via each result's ``index``). Higher is more relevant.
        An empty ``texts`` yields an empty list without a network round-trip.
        """
        if not texts:
            return []

        response = self._client.post(
            self.path,
            json={"model": self.model, "query": query, "documents": texts},
        )
        response.raise_for_status()
        results = response.json().get("results", [])

        scores = [0.0] * len(texts)
        seen = 0
        for item in results:
            index = item.get(_INDEX_FIELD)
            if not isinstance(index, int) or not 0 <= index < len(texts):
                continue
            scores[index] = self._extract_score(item)
            seen += 1

        if seen != len(texts):
            raise ValueError(
                "Rerank response covered "
                f"{seen}/{len(texts)} candidates; refusing partial ranking"
            )
        return scores
