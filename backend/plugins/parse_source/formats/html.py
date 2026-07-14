"""HTML format parser: extract readable markdown from HTML via trafilatura."""

from __future__ import annotations

from backend.plugins.parse_source.formats.base import FormatParser, FormatParserConfig
from backend.shared.content_type import APPLICATION_XHTML_XML, TEXT_HTML


class HtmlFormatParser(FormatParser):
    config = FormatParserConfig(
        name="html",
        label="HTML",
        content_types=(TEXT_HTML, APPLICATION_XHTML_XML),
    )

    def parse(self, content: str, url: str = "") -> str:
        # Imported lazily: trafilatura is heavy and discovery imports this
        # module at process start.
        import trafilatura

        return (
            trafilatura.extract(
                content,
                url=url,
                favor_precision=True,
                include_links=True,
                include_images=False,
                include_comments=False,
                output_format="markdown",
            )
            or ""
        )
