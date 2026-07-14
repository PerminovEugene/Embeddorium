"""Discovery/lookup for per-format parser plugins.

Walks :mod:`backend.plugins.parse_source.formats` for concrete
:class:`~backend.plugins.parse_source.formats.base.FormatParser` subclasses (via
the shared :func:`backend.plugins._strategy_discovery.discover_strategies`),
instantiates one of each, and indexes them by ``name`` (for the explicit parser
override) and by declared content type (for content-type selection). Discovery
runs once per process and is cached.
"""

from __future__ import annotations

from backend.plugins._strategy_discovery import discover_strategies
from backend.plugins.parse_source.formats.base import FormatParser
from backend.shared.content_type import normalize_content_type

_by_name: dict[str, FormatParser] | None = None
_by_content_type: dict[str, FormatParser] | None = None


def _instances() -> dict[str, FormatParser]:
    global _by_name
    if _by_name is None:
        import backend.plugins.parse_source.formats as pkg

        _by_name = {
            name: cls() for name, cls in discover_strategies(pkg, FormatParser).items()
        }
    return _by_name


def _content_type_index() -> dict[str, FormatParser]:
    global _by_content_type
    if _by_content_type is None:
        index: dict[str, FormatParser] = {}
        for parser in _instances().values():
            for content_type in parser.config.content_types:
                index.setdefault(normalize_content_type(content_type), parser)
        _by_content_type = index
    return _by_content_type


def get_parser(content_type: str | None) -> FormatParser | None:
    """Return the parser registered for *content_type*, or ``None``."""
    return _content_type_index().get(normalize_content_type(content_type))


def get_parser_by_name(name: str | None) -> FormatParser | None:
    """Return the parser registered under *name* (e.g. ``"html"``), or ``None``.

    ``None``/``"auto"`` returns ``None`` so callers fall back to content-type
    selection; an unknown name also returns ``None``.
    """
    if not name or name == "auto":
        return None
    return _instances().get(name.strip().lower())
