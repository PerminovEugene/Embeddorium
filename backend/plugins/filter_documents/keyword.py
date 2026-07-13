"""Keyword relevance strategy for the ``filter_documents`` actor.

The gate supports two independent comma-separated keyword lists:

- ``keywords`` — the *include* list. Title-authoritative with a body fallback
  for untitled documents (the actor extracts an XML title, which is empty for
  non-XML/HTML sources — see ``matches_keywords``). An empty include list means
  no include restriction.
- ``exclude_keywords`` — the *exclude* list. Consulted against the title *and*
  the body; any match drops the document.

Decision: when ``enabled`` is off every document passes; otherwise a document
is relevant iff the include gate passes AND no exclude keyword matches (exclude
wins). Empty lists collapse to the historical behavior.
"""

from __future__ import annotations

from backend.plugins._fields import FieldSpec
from backend.plugins.filter_documents.base import FilterStrategy, FilterStrategyConfig
from backend.shared.parsers.keyword_filter import matches_any, matches_keywords


def _parse_keywords(raw: str) -> list[str]:
    """Split a comma-separated keyword string into a clean list ([] if empty)."""
    return [kw.strip() for kw in raw.split(",") if kw.strip()]


class KeywordFilter(FilterStrategy):
    config = FilterStrategyConfig(
        name="keyword",
        label="Keyword relevance",
        description=(
            "Keeps documents matching an include-keyword list and drops any "
            "matching an exclude-keyword list; passes everything when disabled "
            "or when no keywords are set."
        ),
        fields=[
            FieldSpec(
                key="enabled",
                label="Enable relevance gate",
                type="checkbox",
                default=True,
            ),
            FieldSpec(
                key="keywords",
                label="Include keywords",
                type="text",
                default="",
                placeholder="income, tax",
            ),
            FieldSpec(
                key="exclude_keywords",
                label="Exclude keywords",
                type="text",
                default="",
                placeholder="draft, repealed",
            ),
        ],
    )

    def is_relevant(self, *, title: str | None, text: str) -> bool:
        if not self._get("enabled"):
            return True

        # Exclude wins: any exclude keyword in the title OR body drops the doc.
        # matches_any consults both fields (not the title-authoritative fallback
        # matches_keywords uses), so web/HTML docs with an empty title are gated
        # on their body content.
        exclude = _parse_keywords(self._get("exclude_keywords")) or None
        if matches_any(title, text=text, keywords=exclude):
            return False

        # Include gate: empty list passes everything; otherwise the title (or
        # body when the title is absent) must contain at least one keyword.
        include = _parse_keywords(self._get("keywords")) or None
        return matches_keywords(title, text=text, keywords=include)
