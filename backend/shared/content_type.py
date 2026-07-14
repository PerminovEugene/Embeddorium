"""Shared content-type (MIME) policy.

Pure MIME string helpers plus the canonical set of content types the ingestion
pipeline knows how to turn into text. This is genuine cross-cutting policy, not
parsing: the ``fetch_source`` strategy uses it to reject unfetchable content
early, and the ``parse_source`` format-parser plugins declare the subset each of
them handles. It therefore lives in ``shared`` rather than inside either plugin
— a plugin importing a sibling plugin's internals (``fetch_source`` reaching
into ``parse_source``) would be the wrong coupling.

Adding a brand-new *content type* means both a
:class:`~backend.plugins.parse_source.formats.base.FormatParser` plugin that
declares it *and* an entry in :data:`SUPPORTED_CONTENT_TYPES` here. Swapping the
library for an existing format, or adding a custom parser for one of these
types, is a pure plugin drop-in that needs no change here.
"""

from __future__ import annotations

TEXT_HTML = "text/html"
APPLICATION_XHTML_XML = "application/xhtml+xml"
TEXT_PLAIN = "text/plain"
APPLICATION_XML = "application/xml"
TEXT_XML = "text/xml"

# Every content type the pipeline accepts. Kept in lock-step with the format
# parsers' declared ``content_types`` by a discovery test (see
# ``backend/tests/plugins/parse_source/test_formats.py``).
SUPPORTED_CONTENT_TYPES = frozenset(
    {
        TEXT_HTML,
        APPLICATION_XHTML_XML,
        TEXT_PLAIN,
        APPLICATION_XML,
        TEXT_XML,
    }
)


def normalize_content_type(content_type: str | None) -> str:
    """Strip parameters/charset and lowercase, e.g. ``text/html; charset=utf-8``."""
    if not content_type:
        return ""
    return content_type.split(";")[0].strip().lower()


def is_supported(content_type: str | None) -> bool:
    """Return whether *content_type* is one the pipeline can turn into text."""
    return normalize_content_type(content_type) in SUPPORTED_CONTENT_TYPES
