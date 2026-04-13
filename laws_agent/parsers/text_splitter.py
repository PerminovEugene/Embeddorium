from langchain_text_splitters import MarkdownTextSplitter

from laws_agent.parsers.link_extractor import LinkExtractor, LinkInfo


class Chunk:
    text: str
    links: LinkInfo


class TextSplitter:
    def __init__(self) -> None:
        self.extractor = LinkExtractor()
        self.splitter = MarkdownTextSplitter(
            chunk_size=1200,
            chunk_overlap=150,
        )

    def split(self, text: str) -> list[Chunk]:
        chunks = self.splitter.split_text(text)
        return [
            {"text": chunk, "links": self.extractor.extract_links(chunk)}
            for chunk in chunks
        ]
