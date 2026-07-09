"""Sliding-window chunker.

Splits text into overlapping windows of whole words: each chunk holds
``window_size`` words, and the window advances by ``step_size`` words between
chunks. When ``step_size`` is smaller than ``window_size`` the windows
overlap (the classic sliding window); when equal, they tile with no overlap.

Word-based rather than character-based so window boundaries never fall inside
a word. Dependency-free and deterministic — no external splitter.
"""

from __future__ import annotations

import re
from typing import List

from backend.plugins.chunkers.base import (
    Chunk,
    Chunker,
    ChunkerConfig,
    ChunkerField,
    ChunkInput,
)

_WORD_RE = re.compile(r"\S+")


class SlidingWindowChunker(Chunker):
    """Emits overlapping fixed-width windows of words, advancing by a fixed
    step between chunks."""

    config = ChunkerConfig(
        name="text_sliding_window",
        label="Sliding window",
        description=(
            "Emits overlapping windows of whole words: each chunk holds "
            "'window size' words and the window advances by 'step size' words. "
            "A smaller step means more overlap between adjacent chunks."
        ),
        fields=[
            ChunkerField(
                key="window_size",
                label="Window size (words)",
                type="number",
                default=200,
                min=1,
            ),
            ChunkerField(
                key="step_size",
                label="Step size (words)",
                type="number",
                default=100,
                min=1,
            ),
        ],
    )

    def chunk(self, ctx: ChunkInput) -> List[Chunk]:
        if not ctx.text or not ctx.text.strip():
            return []

        window = max(1, int(self._get("window_size")))
        step = max(1, int(self._get("step_size")))

        # Match words with their spans so each chunk can report where it
        # sits in the source text: start of its first word to end of its
        # last word (chunk text normalises inter-word whitespace, but the
        # source range is exact).
        words = list(_WORD_RE.finditer(ctx.text))
        if not words:
            return []

        chunks: List[Chunk] = []
        for start in range(0, len(words), step):
            window_words = words[start : start + window]
            if window_words:
                chunks.append(
                    Chunk(
                        text=" ".join(m.group() for m in window_words),
                        start_offset=window_words[0].start(),
                        end_offset=window_words[-1].end(),
                    )
                )
            # The final window reaches the end of the document; stop so we
            # don't emit further chunks that only repeat the tail.
            if start + window >= len(words):
                break

        return chunks
