"""Legal-structure-aware chunker for Estonian Juurakt-format act XML.

This plugin owns the whole legal chunking stack as a subpackage:

* ``reader`` parses raw Juurakt act XML into a typed tree
  (:class:`~backend.plugins.chunkers.legal_xml.reader.LegalDocument`);
* ``chunker`` turns that tree into ``§``-based
  :class:`~backend.plugins.chunkers.legal_xml.chunker.LegalChunk` objects;
* ``inspect`` is a read-only CLI for eyeballing the result.

The plugin drives ``reader`` → ``chunker`` directly and maps the result onto
the plugin :class:`~backend.plugins.chunkers.base.Chunk`. Link extraction is
deliberately *not* done here — the ``chunk_document`` actor re-extracts links
from every returned chunk's text, so the plugin ``Chunk`` carries no ``links``.

Falls back to the markdown chunker whenever ``ctx.raw_content`` is missing or
does not parse as a Juurakt act, so this chunker always returns *some* chunks
rather than leaving a document unchunked just because it turned out not to be
an act.
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.plugins.chunkers.base import (
    Chunk,
    Chunker,
    ChunkerConfig,
    ChunkerField,
    ChunkInput,
)
from backend.plugins.chunkers.legal_xml.chunker import (
    LegalChunkConfig,
    LegalChunker,
    build_report,
    log_report,
)
from backend.plugins.chunkers.legal_xml.reader import LegalXmlReader
from backend.plugins.chunkers.text_markdown import MarkdownChunker


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
                key="target_tokens",
                label="Target tokens",
                type="number",
                default=600,
                min=1,
            ),
            ChunkerField(
                key="max_tokens",
                label="Max tokens",
                type="number",
                default=1100,
                min=1,
            ),
            ChunkerField(
                key="min_tokens",
                label="Min tokens",
                type="number",
                default=100,
                min=0,
            ),
        ],
    )

    def __init__(self, settings: Dict[str, Any]) -> None:
        super().__init__(settings)
        self._config = LegalChunkConfig(
            target_tokens=int(self._get("target_tokens")),
            max_tokens=int(self._get("max_tokens")),
            min_tokens=int(self._get("min_tokens")),
        )
        self._reader = LegalXmlReader()
        self._chunker = LegalChunker(self._config)
        # Fallback path for non-XML/non-act content; shares no state with the
        # legal chunker above, so its own (unrelated) fields default cleanly.
        self._fallback = MarkdownChunker({})

    def chunk(self, ctx: ChunkInput) -> List[Chunk]:
        if ctx.raw_content:
            doc = self._reader.parse(
                ctx.raw_content, source_url=ctx.source_url, language=ctx.language
            )
            if doc is not None:
                legal_chunks = self._chunker.chunk(doc)
                log_report(build_report(legal_chunks, self._config.min_tokens))
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
