"""The parse_source strategy plugin interface.

A parse strategy owns the content-to-text half of the ``parse_source`` actor:
picking a parser for a fetched source and turning its raw bytes into
normalized text. Everything shared — acquiring/locking the target, loading the
persisted ``SourceFetch``, writing the parsed-text artefact, building the
``Document`` provenance row and enqueueing ``chunk_document`` — stays in the
actor, so a strategy is a near-pure function ``(raw, content_type) -> text``.

The single built-in strategy (``content_type``) reproduces the actor's
previous behavior exactly: an explicit ``parser`` override (anything other than
``"auto"``) wins, otherwise the parser is selected by content type; an
unresolvable parser yields ``None`` so the actor marks the target
SKIPPED_UNSUPPORTED.

Subclasses set a class-level ``config`` (a :class:`ParseStrategyConfig`) and
implement :meth:`parse`. ``__init__`` resolves the raw ``settings`` dict (as
stored in ``ParseSourceSettings``) against ``config.fields`` with per-field
defaults — the same settings-resolution convenience the chunker plugins offer
— so a subclass reads resolved values via :meth:`_get` instead of
re-implementing default handling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from backend.plugins._fields import FieldSpec
from backend.plugins.structured_data import ParsedDocument


@dataclass(frozen=True)
class ParseStrategyConfig:
    """Static, UI-facing description of a parse strategy plugin.

    ``name`` is the stable id the strategy is looked up under in the registry;
    ``fields`` describes the knobs the actor reads out of
    :class:`~backend.shared.models.pipeline_run.ParseSourceSettings`, served
    camelCased like every other plugin config.
    """

    name: str
    label: str
    description: str
    fields: list[FieldSpec] = field(default_factory=list)


class ParseStrategy(ABC):
    """Base class every parse_source strategy plugin subclasses."""

    config: ClassVar[ParseStrategyConfig]

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        settings = settings or {}
        self.settings: dict[str, Any] = {
            f.key: settings.get(f.key, f.default) for f in self.config.fields
        }

    def _get(self, key: str) -> Any:
        """Return the resolved value for a declared field key."""
        return self.settings[key]

    @abstractmethod
    def parse(
        self, *, raw: str, content_type: str | None, final_url: str
    ) -> str | ParsedDocument | None:
        """Return *raw* parsed to normalized text, or ``None`` when no parser
        supports it (the actor then marks the target SKIPPED_UNSUPPORTED)."""
        raise NotImplementedError
