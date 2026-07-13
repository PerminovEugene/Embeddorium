"""The filter_documents strategy plugin interface.

A filter strategy owns the relevance decision of the ``filter_documents``
actor: given a document's title and body text, decide whether it should
advance down the pipeline. Everything shared — acquiring/locking the target,
loading the ``SourceFetch``, reading the raw content, extracting the title,
status transitions and enqueueing ``parse_source`` — stays in the actor, so a
strategy is a near-pure predicate ``(title, text) -> bool``.

The single built-in strategy (``keyword``) gates on two independent keyword
lists: when the gate is disabled every document passes; otherwise a document
is relevant iff no *exclude* keyword matches its title or body (exclude wins)
and — when an *include* list is set — its title (or body when the title is
absent) matches at least one include keyword. Empty lists let everything
through.

Subclasses set a class-level ``config`` (a :class:`FilterStrategyConfig`) and
implement :meth:`is_relevant`. ``__init__`` resolves the raw ``settings`` dict
(as stored in ``FilterDocumentsSettings``) against ``config.fields`` with
per-field defaults — the same settings-resolution convenience the chunker
plugins offer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from backend.plugins._fields import FieldSpec


@dataclass(frozen=True)
class FilterStrategyConfig:
    """Static, UI-facing description of a filter strategy plugin.

    ``name`` is the stable id the strategy is looked up under in the registry;
    ``fields`` describes the knobs the actor reads out of
    :class:`~backend.shared.models.pipeline_run.FilterDocumentsSettings`,
    served camelCased like every other plugin config.
    """

    name: str
    label: str
    description: str
    fields: list[FieldSpec] = field(default_factory=list)


class FilterStrategy(ABC):
    """Base class every filter_documents strategy plugin subclasses."""

    config: ClassVar[FilterStrategyConfig]

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        settings = settings or {}
        self.settings: dict[str, Any] = {
            f.key: settings.get(f.key, f.default) for f in self.config.fields
        }

    def _get(self, key: str) -> Any:
        """Return the resolved value for a declared field key."""
        return self.settings[key]

    @abstractmethod
    def is_relevant(self, *, title: str | None, text: str) -> bool:
        """Return whether the document should advance down the pipeline."""
        raise NotImplementedError
