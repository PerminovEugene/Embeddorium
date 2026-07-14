"""XML format parser for the Estonian legal-act (``Juurakt``) format.

Extracts readable plain text from an act document: the title (``pealkiri``) is
rendered as a heading followed by the flattened body text. The title is sourced
from the shared :func:`backend.shared.xml_utils.extract_act_title` helper (also
used by ``filter_documents``), so the two consumers share one definition.
"""

from __future__ import annotations

from backend.plugins.parse_source.formats.base import FormatParser, FormatParserConfig
from backend.shared.content_type import APPLICATION_XML, TEXT_XML
from backend.shared.xml_utils import extract_act_title, parse_tree


class XmlFormatParser(FormatParser):
    config = FormatParserConfig(
        name="xml",
        label="XML",
        content_types=(APPLICATION_XML, TEXT_XML),
    )

    def parse(self, content: str, url: str = "") -> str:
        root = parse_tree(content)
        if root is None:
            return (content or "").strip()

        title = extract_act_title(content)
        body_text = self._collapse_whitespace(" ".join(root.itertext()))

        if not title:
            return body_text

        # The title text also appears inside the body via itertext(); keep it
        # as a heading and let it appear in the body too rather than trying
        # to surgically remove it, which would be brittle.
        return f"{title}\n\n{body_text}".strip()

    @staticmethod
    def _collapse_whitespace(text: str) -> str:
        return " ".join(text.split())
