"""Small shared XML helpers for the Estonian legal-act (``Juurakt``) format.

``extract_act_title`` pulls the act's ``pealkiri`` (title) out of raw act XML.
It is shared because two unrelated consumers need it without depending on each
other's internals: the ``filter_documents`` actor (to obtain a document title
for keyword filtering) and the ``parse_source`` XML format parser (to render the
title as a heading). Keeping it here avoids ``filter_documents`` reaching into a
``parse_source`` plugin module.
"""

from __future__ import annotations

from xml.etree import ElementTree

_TITLE_TAG = "pealkiri"


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_tree(content: str) -> ElementTree.Element | None:
    """Parse *content* into an element tree, or ``None`` when it is not XML."""
    try:
        return ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return None


def extract_act_title(content: str) -> str:
    """Return the act's title (``pealkiri``), or ``""`` if it can't be found."""
    root = parse_tree(content)
    if root is None:
        return ""

    for elem in root.iter():
        if _strip_namespace(elem.tag) == _TITLE_TAG:
            return "".join(elem.itertext()).strip()

    return ""
