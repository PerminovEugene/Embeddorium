"""Content-type parse strategy: override-else-content-type parser selection.

Carries over the old parse_source actor behavior verbatim: an explicit
``parser`` override (anything but ``"auto"``) wins, otherwise the parser is
picked by the fetched source's content type via the parser registry. An
unresolvable parser (unknown content type, override naming a parser that does
not exist and no content-type match) yields ``None`` so the actor marks the
target SKIPPED_UNSUPPORTED.

The ``parser`` field's options mirror what the parser registry exposes by name
plus ``auto``; ``pdf`` is offered so the UI can present it, but it has no
parser yet, so selecting it falls back to content-type selection exactly as
before.
"""

from __future__ import annotations

from backend.plugins._fields import FieldSpec
from backend.plugins.parse_source.base import ParseStrategy, ParseStrategyConfig
from backend.plugins.parse_source.formats.registry import get_parser, get_parser_by_name


class ContentTypeParse(ParseStrategy):
    config = ParseStrategyConfig(
        name="content_type",
        label="By content type",
        description=(
            "Selects a parser by the fetched source's content type, unless an "
            "explicit parser override is set."
        ),
        fields=[
            FieldSpec(
                key="parser",
                label="Parser",
                type="select",
                default="auto",
                options=[
                    {"value": "auto", "label": "Auto (by content type)"},
                    {"value": "html", "label": "HTML"},
                    {"value": "xml", "label": "XML"},
                    {"value": "plain", "label": "Plain text"},
                    {"value": "pdf", "label": "PDF"},
                ],
            ),
        ],
    )

    def parse(
        self, *, raw: str, content_type: str | None, final_url: str
    ) -> str | None:
        parser = get_parser_by_name(self._get("parser")) or get_parser(content_type)
        if parser is None:
            return None
        return parser.parse(raw, final_url)
