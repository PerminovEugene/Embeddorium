"""Parser for the Estonian legal-act XML format (``Juurakt`` schema).

Acts are exported as ``oigusakt`` documents with a default namespace
(``xmlns="Juurakt"``); the act title lives at ``aktinimi/nimi/pealkiri`` and
the body text is nested under ``sisu`` (``paragrahv`` -> ``loige`` ->
``sisuTekst`` -> ``tavatekst``, plus assorted inline elements). Rather than
hard-coding every element name, ``itertext()`` walks the whole tree and the
title is rendered as a heading followed by the remaining text content.
"""

from __future__ import annotations

from xml.etree import ElementTree

_TITLE_TAG = "pealkiri"


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_tree(content: str) -> ElementTree.Element | None:
    try:
        return ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return None


def extract_act_title(content: str) -> str:
    """Return the act's title (``pealkiri``), or ``""`` if it can't be found."""
    root = _parse_tree(content)
    if root is None:
        return ""

    for elem in root.iter():
        if _strip_namespace(elem.tag) == _TITLE_TAG:
            return "".join(elem.itertext()).strip()

    return ""


class XmlParser:
    """Extracts readable plain text from an Estonian legal-act XML document."""

    def parse(self, content: str, url: str = "") -> str:
        root = _parse_tree(content)
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
