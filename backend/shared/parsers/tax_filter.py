"""Tax-relevance classifier for the local-file (XML) ingestion chain.

``filter_tax_acts`` uses this to keep only tax-related Estonian acts out of
the full ~5600-file dump. The title is authoritative (Estonian act titles are
descriptive, e.g. "Value Added Tax Act", "Customs Act"); the raw text is only
consulted as a fallback when the title is empty or unhelpful.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

# Curated, case-insensitive keyword set for Estonian tax law in English.
# Kept deliberately narrow (whole-word/phrase matches only) to avoid
# false positives on unrelated acts that happen to contain a generic word
# like "duty" (e.g. "duties of an official") in a non-tax sense.
TAX_KEYWORDS = frozenset(
    {
        "tax",
        "taxes",
        "taxation",
        "taxable",
        "excise",
        "customs",
        "duty",
        "duties",
        "vat",
        "value added tax",
        "levy",
        "levies",
        "social tax",
        "income tax",
        "land tax",
        "gambling tax",
        "heavy goods vehicle tax",
        "tobacco excise",
        "alcohol excise",
        "fuel excise",
    }
)

_WORD_BOUNDARY_PATTERNS = {
    keyword: re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)
    for keyword in TAX_KEYWORDS
}


def _patterns_for(keywords: Optional[Iterable[str]]):
    """Return compiled whole-word patterns for *keywords*, or the default set.

    ``None``/empty falls back to the curated :data:`TAX_KEYWORDS`. A custom
    list is compiled on the fly (used by the ``filter_tax_acts`` actor when a
    run overrides the keyword set).
    """
    if not keywords:
        return _WORD_BOUNDARY_PATTERNS.values()
    return [
        re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        for kw in keywords
        if kw
    ]


def _contains_tax_keyword(text: str, patterns) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def is_tax_related(
    title: str,
    text: str | None = None,
    *,
    keywords: Optional[Iterable[str]] = None,
) -> bool:
    """Return ``True`` if the act is tax-related.

    The title is authoritative: any keyword match there is sufficient. If the
    title is empty (or matches nothing), fall back to scanning ``text`` for
    the same strong signals. ``keywords`` overrides the curated default set
    when a run configures its own list.
    """
    patterns = _patterns_for(keywords)

    if title and _contains_tax_keyword(title, patterns):
        return True

    if not title and text:
        return _contains_tax_keyword(text, patterns)

    return False
