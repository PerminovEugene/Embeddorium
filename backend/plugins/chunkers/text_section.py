"""Header-based chunker: one chunk per markdown section.

Ports the ``_split_by_section`` logic that used to live on
``TextSplitter(strategy="section")`` verbatim. Splits on markdown headers
(``#``/``##``/``###``); when the text has no headers at all it falls back to
blank-line paragraph splitting so short, header-less documents still get
sensible chunks instead of one giant blob.
"""

from __future__ import annotations

import re
from typing import List

from langchain_text_splitters import MarkdownHeaderTextSplitter

from backend.plugins.chunkers.base import Chunk, Chunker, ChunkerConfig, ChunkInput

_SECTION_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]
_PARAGRAPH_RE = re.compile(r"\n{2,}")


class SectionChunker(Chunker):
    """Splits on markdown headers; falls back to paragraphs when headerless."""

    config = ChunkerConfig(
        name="text_section",
        label="Section (headers)",
        description=(
            "Splits on markdown headers (#, ##, ###) — one chunk per section. "
            "Falls back to blank-line paragraph splitting when the document "
            "has no headers."
        ),
    )

    def chunk(self, ctx: ChunkInput) -> List[Chunk]:
        if not ctx.text:
            return []
        return [Chunk(text=text) for text in self._split_by_section(ctx.text)]

    @staticmethod
    def _split_by_section(text: str) -> List[str]:
        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=_SECTION_HEADERS,
            strip_headers=False,
        )
        docs = header_splitter.split_text(text)
        # If there is only one doc and it equals the whole input, no headers
        # were found — fall back to blank-line paragraph splits.
        if len(docs) <= 1:
            raw = docs[0].page_content if docs else text
            if not any(
                raw.lstrip().startswith(marker)
                for marker in ("# ", "## ", "### ")
            ):
                paragraphs = [p.strip() for p in _PARAGRAPH_RE.split(text)]
                return [p for p in paragraphs if p]
        return [doc.page_content for doc in docs if doc.page_content.strip()]
