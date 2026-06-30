import logging
import time
from typing import List, Optional, Sequence

import numpy as np
from langchain_ollama import OllamaEmbeddings

# Maximum number of texts sent to Ollama in a single HTTP request.  Large
# batches can cause the model-runner subprocess to close the connection with
# an EOF 400, so we keep each payload small regardless of what the caller
# hands us.
_INTERNAL_BATCH_SIZE: int = 16

# Number of *extra* attempts after the first failure.  The Ollama runner can
# briefly disappear when the host swaps models; a short retry rides that out.
_EMBED_RETRIES: int = 2
_RETRY_BACKOFF: float = 1.0  # seconds between attempts

log = logging.getLogger(__name__)


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

    def _embed_batch_with_retry(self, texts: List[str]) -> List[List[float]]:
        """Call ``embed_documents`` for *texts* with up to ``_EMBED_RETRIES`` retries.

        Raises the last exception if every attempt fails.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1 + _EMBED_RETRIES):
            try:
                return self._client.embed_documents(texts)
            except Exception as exc:
                last_exc = exc
                if attempt < _EMBED_RETRIES:
                    log.warning(
                        "Ollama embed attempt %d/%d failed (%s: %s);"
                        " retrying in %.1fs",
                        attempt + 1,
                        1 + _EMBED_RETRIES,
                        type(exc).__name__,
                        exc,
                        _RETRY_BACKOFF,
                    )
                    time.sleep(_RETRY_BACKOFF)
        raise last_exc  # type: ignore[misc]

    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int = 1,
        show_progress_bar: bool = False,
        normalize_embeddings: bool = False,
    ) -> np.ndarray:
        """Embed *sentences* via the Ollama HTTP API.

        ``show_progress_bar`` is accepted for interface compatibility with
        SentenceTransformer but unused.

        Texts are sent in batches of at most
        ``max(batch_size, _INTERNAL_BATCH_SIZE)`` to avoid overwhelming the
        Ollama runner with a single oversized request.  Empty /
        whitespace-only strings are replaced with a single space before
        sending so the runner never receives a blank input (which triggers an
        EOF 400) — the output vector count always equals the input count,
        keeping positional alignment with callers that ``zip`` queries to
        embeddings by index.
        """
        texts = list(sentences)

        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        # Replace empty / whitespace-only strings with a single space so
        # Ollama never sees a blank input, while still emitting one vector
        # per input row.
        safe_texts = [t if t.strip() else " " for t in texts]

        # Honour explicit caller batch sizes above the internal minimum, but
        # never go below it — a batch_size=1 from legacy callers would be
        # needlessly slow *and* still unsafe for very long single texts.
        effective_batch = max(batch_size, _INTERNAL_BATCH_SIZE)

        all_vectors: List[List[float]] = []
        for start in range(0, len(safe_texts), effective_batch):
            chunk = safe_texts[start : start + effective_batch]
            vectors = self._embed_batch_with_retry(chunk)
            all_vectors.extend(vectors)

        embeddings = np.asarray(all_vectors, dtype=np.float32)

        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms

        return embeddings
