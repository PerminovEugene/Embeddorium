from typing import Sequence

import numpy as np

# Default FastEmbed model — a small, fast 384-dim English embedding model.
_DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class FastembedEmbedClient:
    """Adapts Qdrant's ``fastembed.TextEmbedding`` to the SentenceTransformer-like
    interface (``encode`` / ``get_embedding_dimension``) expected by the
    embed_chunks actor, so swapping providers needs no change to its
    batching/upsert logic.

    FastEmbed is fully local: it downloads an ONNX model and computes vectors
    in-process via onnxruntime — no server, no torch. ``fastembed`` is imported
    lazily so this module stays import-light, and the model is constructed with
    ``lazy_load`` so the download only happens on the first ``encode`` call, not
    at construction.
    """

    def __init__(self, model: str | None = None) -> None:
        # Deferred import: keep this module import-light for callers that never
        # touch the fastembed path.
        from fastembed import TextEmbedding

        self.model = model or _DEFAULT_MODEL
        self._client = TextEmbedding(model_name=self.model, lazy_load=True)
        self._dimension: int | None = None

    def get_embedding_dimension(self) -> int:
        """Return the vector dimension for the configured model.

        Read from FastEmbed's model metadata when available (no download); fall
        back to a one-shot probe embedding otherwise. The result is cached.
        """
        if self._dimension is None:
            self._dimension = self._lookup_dimension()
        return self._dimension

    def _lookup_dimension(self) -> int:
        from fastembed import TextEmbedding

        for spec in TextEmbedding.list_supported_models():
            if spec.get("model") == self.model:
                dim = spec.get("dim")
                if isinstance(dim, int):
                    return dim
        # Unknown model (e.g. a custom one): probe with a single embedding.
        probe = next(iter(self._client.embed(["dimension probe"])))
        return int(np.asarray(probe).shape[-1])

    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int = 1,
        show_progress_bar: bool = False,
        normalize_embeddings: bool = False,
    ) -> np.ndarray:
        """Embed *sentences* via FastEmbed's in-process ONNX model.

        ``show_progress_bar`` is accepted for interface compatibility with
        SentenceTransformer but unused. ``fastembed`` returns unnormalized
        vectors, so L2 normalization is applied here when requested, matching
        the mock/ollama clients. The output vector count always equals the input
        count, keeping positional alignment with callers that ``zip`` inputs to
        embeddings by index.
        """
        texts = list(sentences)

        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        vectors = list(self._client.embed(texts, batch_size=batch_size))
        embeddings = np.asarray(vectors, dtype=np.float32)

        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms

        return embeddings
