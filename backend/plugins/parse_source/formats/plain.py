"""Plain-text format parser: the body is already the text."""

from __future__ import annotations

from backend.plugins.parse_source.formats.base import FormatParser, FormatParserConfig
from backend.shared.content_type import TEXT_PLAIN


class PlainTextFormatParser(FormatParser):
    config = FormatParserConfig(
        name="plain",
        label="Plain text",
        content_types=(TEXT_PLAIN,),
    )

    def parse(self, content: str, url: str = "") -> str:
        return (content or "").strip()
