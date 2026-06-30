class PlainTextParser:
    """Trivial parser for ``text/plain`` sources: the body is already the text."""

    def parse(self, content: str, url: str = "") -> str:
        return (content or "").strip()
