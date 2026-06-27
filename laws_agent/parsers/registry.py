"""Content-type → parser registry.

Keeps the supported-content-type decision and parser selection in one place so
``fetch_source`` can reject unsupported types early and ``parse_source`` can
pick the right parser. Adding a PDF/DOCX parser later is a one-line addition
here plus the parser class — no actor changes.
"""

from __future__ import annotations

from typing import Optional, Protocol

from laws_agent.parsers.html_parser import HtmlParser
from laws_agent.parsers.plain_text_parser import PlainTextParser
from laws_agent.parsers.xml_parser import XmlParser

# Bump when parsing output changes in a way that should invalidate provenance.
PARSER_VERSION = "1"


class Parser(Protocol):
    def parse(self, content: str, url: str = "") -> str: ...


_HTML = HtmlParser()
_PLAIN = PlainTextParser()
_XML = XmlParser()

_REGISTRY: dict[str, Parser] = {
    "text/html": _HTML,
    "application/xhtml+xml": _HTML,
    "text/plain": _PLAIN,
    "application/xml": _XML,
    "text/xml": _XML,
}


def normalize_content_type(content_type: Optional[str]) -> str:
    """Strip parameters/charset and lowercase, e.g. ``text/html; charset=utf-8``."""
    if not content_type:
        return ""
    return content_type.split(";")[0].strip().lower()


def get_parser(content_type: Optional[str]) -> Optional[Parser]:
    return _REGISTRY.get(normalize_content_type(content_type))


def is_supported(content_type: Optional[str]) -> bool:
    return get_parser(content_type) is not None
