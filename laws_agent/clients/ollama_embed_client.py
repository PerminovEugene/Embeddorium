from typing import Sequence

import numpy as np
from langchain_ollama import OllamaEmbeddings


class OllamaEmbedClient:
    """Adapts ``OllamaEmbeddings`` to the SentenceTransformer-like interface
    (``encode`` / ``get_embedding_dimension``) expected by the embed_chunks
    actor, so swapping providers needs no change to its batching/upsert logic.

    Calls a remote Ollama server over HTTP — no local model load, no torch.
    """

    def __init__(self, model: str, base_url: str) -> None:
        self.model = model
        self.base_url = base_url
        self._client = OllamaEmbeddings(model=model, base_url=base_url)
        self._dimension: int | None = None

    def get_embedding_dimension(self) -> int:
        """Return the vector dimension, probing the server once and caching it."""
        if self._dimension is None:
            probe = self._client.embed_query("dimension probe")
            self._dimension = len(probe)
        return self._dimension

    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int = 1,
        show_progress_bar: bool = False,
        normalize_embeddings: bool = False,
    ) -> np.ndarray:
        """Embed *sentences* via the Ollama HTTP API.

        ``batch_size``/``show_progress_bar`` are accepted for interface
        compatibility with SentenceTransformer.encode but unused — each
        request already sends the whole batch handed to us by the caller.
        """
        vectors = self._client.embed_documents(list(sentences))
        embeddings = np.asarray(vectors, dtype=np.float32)

        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms

        return embeddings
