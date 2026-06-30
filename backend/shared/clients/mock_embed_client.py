from typing import Sequence

import numpy as np


class MockEmbedClient:
    """Drop-in replacement for a SentenceTransformer model.

    Generates random vectors instead of running a real embedding model, so the
    crawl/embed pipeline can be exercised quickly in tests or local dry runs.
    """

    def __init__(self, dimension: int, seed: int | None = None) -> None:
        self.dimension = dimension
        self._rng = np.random.default_rng(seed)

    def get_embedding_dimension(self) -> int:
        return self.dimension

    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int = 1,
        show_progress_bar: bool = False,
        normalize_embeddings: bool = False,
    ) -> np.ndarray:
        embeddings = self._rng.standard_normal((len(sentences), self.dimension))

        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms

        return embeddings
