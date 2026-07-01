import re
from dataclasses import dataclass, field
from typing import List

from langchain_text_splitters import MarkdownHeaderTextSplitter, MarkdownTextSplitter

from backend.shared.parsers.chunking_config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHUNK_STRATEGY,
)
from backend.shared.parsers.link_extractor import LinkExtractor, LinkInfo

# Bump when chunking parameters/algorithm change.
CHUNKER_VERSION = "3"

_SECTION_HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]
_PARAGRAPH_RE = re.compile(r"\n{2,}")


@dataclass
class Chunk:
    text: str
    links: List[LinkInfo] = field(default_factory=list)
    # chunk_type/metadata are populated by the legal XML chunker; the generic
    # text strategies leave the defaults (a plain searchable "passage").
    chunk_type: str = "passage"
    metadata: dict = field(default_factory=dict)


class TextSplitter:
    def __init__(
        self,
        strategy: str = CHUNK_STRATEGY,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> None:
        self.strategy = strategy
        self.extractor = LinkExtractor()
        if strategy != "section":
            self.splitter = MarkdownTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

    def _split_by_section(self, text: str) -> List[str]:
        """Split on markdown headers (#/##/###); fall back to paragraphs."""
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

    def split(self, text: str) -> List[Chunk]:
        if not text:
            return []
        if self.strategy == "section":
            raw_chunks = self._split_by_section(text)
        else:
            raw_chunks = self.splitter.split_text(text)
        return [
            Chunk(text=chunk, links=self.extractor.extract_links(chunk))
            for chunk in raw_chunks
        ]
