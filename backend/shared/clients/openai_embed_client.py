"""OpenAI-compatible HTTP embedding client.

This deliberately uses the small HTTP surface shared by OpenAI-compatible
servers instead of binding provider configuration to an SDK. Provider adapters
own URL/API-key/model selection; this client only implements ``encode`` and
``get_embedding_dimension`` for the embedding actor and compare/search paths.
"""

from __future__ import annotations

from typing import Sequence

import httpx
import numpy as np


class OpenAIEmbedClient:
    """SentenceTransformer-like adapter for ``POST /embeddings`` APIs."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(base_url=f"{self.base_url}/", headers=headers)
        self._dimension: int | None = None

    def get_embedding_dimension(self) -> int:
        if self._dimension is None:
            self._dimension = int(self.encode(["dimension probe"]).shape[-1])
        return self._dimension

    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int = 1,
        show_progress_bar: bool = False,
        normalize_embeddings: bool = False,
    ) -> np.ndarray:
        del show_progress_bar
        texts = list(sentences)
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        vectors: list[list[float]] = []
        effective_batch = max(1, batch_size)
        for start in range(0, len(texts), effective_batch):
            response = self._client.post(
                "embeddings",
                json={
                    "model": self.model,
                    "input": texts[start : start + effective_batch],
                },
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            ordered = sorted(data, key=lambda item: item.get("index", 0))
            vectors.extend(item["embedding"] for item in ordered)

        if len(vectors) != len(texts):
            raise ValueError(
                "OpenAI-compatible embeddings response count does not match input count"
            )

        embeddings = np.asarray(vectors, dtype=np.float32)
        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / np.where(norms == 0, 1, norms)
        return embeddings
