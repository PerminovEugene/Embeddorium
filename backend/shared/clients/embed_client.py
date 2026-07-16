"""The structural interface every embedding client satisfies.

The mock, Ollama and OpenAI clients are independent concrete classes (each in
its own module, importing its own backend lazily), but they all expose the same
two-method surface the embed actor and the compare/search paths drive:
:meth:`get_embedding_dimension` and :meth:`encode`
(SentenceTransformer-compatible, returning a ``numpy`` array). This ``Protocol``
names that surface so provider-type adapters can advertise
``build_embed_client() -> EmbedClient`` without any of them sharing a base class
or forcing an eager import of the concrete clients.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

import numpy as np


@runtime_checkable
class EmbedClient(Protocol):
    """A SentenceTransformer-like embedding client."""

    def get_embedding_dimension(self) -> int:
        """Return the vector dimension this client produces."""
        ...

    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int = 1,
        show_progress_bar: bool = False,
        normalize_embeddings: bool = False,
    ) -> np.ndarray:
        """Embed *sentences* into an ``(n, dim)`` array of vectors."""
        ...
