"""Keyword relevance strategy for the ``filter_documents`` actor.

Carries over the actor's previous behavior verbatim: when ``enabled`` is off
every document passes; otherwise the document is relevant iff its title (or
body when the title is absent) contains at least one of the configured
keywords. An empty keyword list means no restriction — everything passes.
"""

from __future__ import annotations

from backend.plugins._fields import FieldSpec
from backend.plugins.filter_documents.base import FilterStrategy, FilterStrategyConfig
from backend.shared.parsers.keyword_filter import matches_keywords


def _parse_keywords(raw: str) -> list[str]:
    """Split a comma-separated keyword string into a clean list ([] if empty)."""
    return [kw.strip() for kw in raw.split(",") if kw.strip()]


class KeywordFilter(FilterStrategy):
    config = FilterStrategyConfig(
        name="keyword",
        label="Keyword relevance",
        description=(
            "Advances a document only when its title or body contains at least "
            "one configured keyword; passes everything when disabled or when no "
            "keywords are set."
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
                label="Keywords",
                type="text",
                default="",
                placeholder="income, tax",
            ),
        ],
    )

    def is_relevant(self, *, title: str | None, text: str) -> bool:
        if not self._get("enabled"):
            return True
        keywords = _parse_keywords(self._get("keywords")) or None
        return matches_keywords(title, text=text, keywords=keywords)
