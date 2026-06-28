from dataclasses import dataclass, field

from langchain_text_splitters import MarkdownTextSplitter

from laws_agent.parsers.chunking_config import CHUNK_OVERLAP, CHUNK_SIZE
from laws_agent.parsers.link_extractor import LinkExtractor, LinkInfo

# Bump when chunking parameters/algorithm change.
CHUNKER_VERSION = "1"


@dataclass
class Chunk:
    text: str
    links: list[LinkInfo] = field(default_factory=list)


class TextSplitter:
    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> None:
        self.extractor = LinkExtractor()
        self.splitter = MarkdownTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def split(self, text: str) -> list[Chunk]:
        return [
            Chunk(text=chunk, links=self.extractor.extract_links(chunk))
            for chunk in self.splitter.split_text(text)
        ]
