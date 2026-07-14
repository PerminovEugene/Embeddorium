"""The per-format parser plugin interface.

A :class:`FormatParser` turns one fetched source's raw content into normalized
text for a specific content type. It declares, via its :class:`FormatParserConfig`:

* ``name`` — the stable id used for the explicit ``parser`` override in the
  ``content_type`` strategy (e.g. ``"html"``), and
* ``content_types`` — the normalized MIME types it handles, used to select it by
  the fetched source's content type.

Parsers are stateless: the registry instantiates one of each and reuses it.
Keep top-level imports cheap — discovery imports every module in this package at
process start — so pull heavy optional dependencies in lazily inside
:meth:`parse`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class FormatParserConfig:
    name: str
    label: str
    content_types: tuple[str, ...] = ()


class FormatParser(ABC):
    config: ClassVar[FormatParserConfig]

    @abstractmethod
    def parse(self, content: str, url: str = "") -> str:
        """Return *content* parsed to normalized text."""
        raise NotImplementedError
