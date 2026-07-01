"""Bridge between the legal XML chunker and the ingestion pipeline.

``chunk_document`` works with :class:`~backend.shared.parsers.text_splitter.Chunk`
objects (text + links + chunk_type + metadata). This adapter parses raw act XML
into the structured tree, runs :class:`LegalChunker`, logs a validation report,
and returns pipeline ``Chunk`` objects. Returns ``None`` when the content is not
parseable Juurakt XML, so callers can fall back to the generic text splitter.
"""

from __future__ import annotations

from typing import List, Optional

from backend.shared.parsers.legal_chunker import (
    LegalChunkConfig,
    LegalChunker,
    build_report,
    log_report,
)
from backend.shared.parsers.legal_xml import LegalXmlReader
from backend.shared.parsers.link_extractor import LinkExtractor
from backend.shared.parsers.text_splitter import Chunk


class LegalXmlChunker:
    def __init__(self, config: Optional[LegalChunkConfig] = None) -> None:
        self.reader = LegalXmlReader()
        self.chunker = LegalChunker(config)
        self.extractor = LinkExtractor()

    def split_xml(
        self, content: str, source_url: str = "", language: str = "en"
    ) -> Optional[List[Chunk]]:
        doc = self.reader.parse(content, source_url=source_url, language=language)
        if doc is None:
            return None
        legal_chunks = self.chunker.chunk(doc)
        log_report(build_report(legal_chunks, self.chunker.cfg.min_tokens))
        return [
            Chunk(
                text=lc.text,
                links=self.extractor.extract_links(lc.text),
                chunk_type=lc.chunk_type,
                metadata=lc.metadata,
            )
            for lc in legal_chunks
        ]
