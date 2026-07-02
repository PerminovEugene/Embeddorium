"""Legal-structure-aware chunker for Estonian Juurakt-format act XML.

Wraps the existing legal chunking stack (``backend.shared.parsers.
legal_xml``/``legal_chunker``/``legal_pipeline`` — see those modules'
docstrings for how the XML tree is parsed and split) instead of
reimplementing it, so this plugin is just an adapter: parse ``ctx
.raw_content`` as a Juurakt act, run the legal chunker, and translate its
``Chunk`` objects (which still carry ``links``, a legacy field) into the
plugin :class:`~backend.plugins.chunkers.base.Chunk` (which does not — the
actor re-extracts links from chunk text for every chunker).

Falls back to the markdown chunker whenever ``ctx.raw_content`` is missing
or does not parse as a Juurakt act, so this chunker always returns *some*
chunks rather than leaving a document unchunked just because it turned out
not to be an act.
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.plugins.chunkers.base import Chunk, Chunker, ChunkerConfig, ChunkerField, ChunkInput
from backend.plugins.chunkers.text_markdown import MarkdownChunker
from backend.shared.parsers.legal_chunker import LegalChunkConfig
from backend.shared.parsers.legal_pipeline import LegalXmlChunker


class LegalXmlChunkerPlugin(Chunker):
    """One chunk per ``§`` section (by default); falls back to markdown
    chunking when the input is not parseable Juurakt XML."""

    config = ChunkerConfig(
        name="legal_xml",
        label="Legal XML (Estonian acts)",
        description=(
            "Structure-aware chunker for Estonian Juurakt-format act XML: one "
            "chunk per § section by default, splitting oversized sections by "
            "subsection/clause ranges instead of arbitrary character offsets. "
            "Falls back to the markdown chunker for non-act content."
        ),
        restrictions="Requires raw XML act content (Juurakt format)",
        fields=[
            ChunkerField(
                key="target_tokens", label="Target tokens", type="number",
                default=600, min=1,
            ),
            ChunkerField(
                key="max_tokens", label="Max tokens", type="number",
                default=1100, min=1,
            ),
            ChunkerField(
                key="min_tokens", label="Min tokens", type="number",
                default=100, min=0,
            ),
        ],
    )

    def __init__(self, settings: Dict[str, Any]) -> None:
        super().__init__(settings)
        self._legal_chunker = LegalXmlChunker(
            LegalChunkConfig(
                target_tokens=int(self._get("target_tokens")),
                max_tokens=int(self._get("max_tokens")),
                min_tokens=int(self._get("min_tokens")),
            )
        )
        # Fallback path for non-XML/non-act content; shares no state with the
        # legal chunker above, so its own (unrelated) fields default cleanly.
        self._fallback = MarkdownChunker({})

    def chunk(self, ctx: ChunkInput) -> List[Chunk]:
        if ctx.raw_content:
            legal_chunks = self._legal_chunker.split_xml(
                ctx.raw_content, source_url=ctx.source_url, language=ctx.language
            )
            if legal_chunks:
                return [
                    Chunk(
                        text=legal_chunk.text,
                        chunk_type=legal_chunk.chunk_type,
                        metadata=legal_chunk.metadata,
                    )
                    for legal_chunk in legal_chunks
                ]
        return self._fallback.chunk(ctx)
