"""Sentence-aware chunker.

Splits text into sentences on ``.``/``!``/``?`` boundaries, then greedily
packs whole sentences into chunks up to ``chunk_size`` characters — a chunk
never cuts a sentence in half. ``chunk_overlap`` re-includes the trailing
sentences of the previous chunk (up to that many characters) at the start of
the next one, so adjacent chunks share context.

Dependency-free (regex only): no NLTK/spaCy model download, so it stays fast
and deterministic in the container and under the ``mock`` embedder in tests.
"""

from __future__ import annotations

import re
from typing import List

from backend.plugins.chunkers._size_fields import size_overlap_fields
from backend.plugins.chunkers.base import Chunk, Chunker, ChunkerConfig, ChunkInput

# Split after sentence-ending punctuation followed by whitespace. Keeps the
# terminator with its sentence. Good enough for prose without a heavy NLP dep.
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


class SentenceChunker(Chunker):
    """Packs whole sentences into chunks up to ``chunk_size``, never splitting
    a sentence mid-way; ``chunk_overlap`` shares trailing sentences between
    adjacent chunks."""

    config = ChunkerConfig(
        name="text_sentence",
        label="Sentence",
        description=(
            "Splits on sentence boundaries (. ! ?) and packs whole sentences "
            "into chunks up to the target size — a chunk never cuts a sentence "
            "in half. Good for keeping semantic units intact."
        ),
        fields=size_overlap_fields(),
    )

    def chunk(self, ctx: ChunkInput) -> List[Chunk]:
        if not ctx.text or not ctx.text.strip():
            return []

        chunk_size = max(1, int(self._get("chunk_size")))
        overlap = max(0, int(self._get("chunk_overlap")))

        sentences = [s for s in (p.strip() for p in _SENTENCE_RE.split(ctx.text)) if s]
        if not sentences:
            return []

        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for sentence in sentences:
            # A single sentence longer than chunk_size becomes its own chunk
            # rather than being dropped or forcing an empty flush.
            addition = len(sentence) + (1 if current else 0)
            if current and current_len + addition > chunk_size:
                chunks.append(" ".join(current))
                current, current_len = self._carry_overlap(current, overlap)

            current.append(sentence)
            current_len += len(sentence) + (1 if current_len else 0)

        if current:
            chunks.append(" ".join(current))

        return [Chunk(text=text) for text in chunks]

    @staticmethod
    def _carry_overlap(sentences: List[str], overlap: int) -> tuple[List[str], int]:
        """Return the trailing sentences (and their joined length) whose total
        length stays within *overlap* characters, to seed the next chunk."""
        if overlap <= 0:
            return [], 0

        carried: List[str] = []
        length = 0
        for sentence in reversed(sentences):
            addition = len(sentence) + (1 if carried else 0)
            if length + addition > overlap:
                break
            carried.insert(0, sentence)
            length += addition
        return carried, length
