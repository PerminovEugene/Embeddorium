"""Tax-relevance classifier for the local-file (XML) ingestion chain.

``filter_tax_acts`` uses this to keep only tax-related Estonian acts out of
the full ~5600-file dump. The title is authoritative (Estonian act titles are
descriptive, e.g. "Value Added Tax Act", "Customs Act"); the raw text is only
consulted as a fallback when the title is empty or unhelpful.
"""

from __future__ import annotations

import re

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


def _contains_tax_keyword(text: str) -> bool:
    return any(pattern.search(text) for pattern in _WORD_BOUNDARY_PATTERNS.values())


def is_tax_related(title: str, text: str | None = None) -> bool:
    """Return ``True`` if the act is tax-related.

    The title is authoritative: any keyword match there is sufficient. If the
    title is empty (or matches nothing), fall back to scanning ``text`` for
    the same strong signals.
    """
    if title and _contains_tax_keyword(title):
        return True

    if not title and text:
        return _contains_tax_keyword(text)

    return False
