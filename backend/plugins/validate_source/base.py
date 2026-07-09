"""The validate_source strategy plugin interface.

A validation strategy owns the source-type-specific half of the
``validate_source`` actor: turning the raw seed value (web URL or local file
path) into its canonical ``original_url``/``normalized_url`` pair, and
deciding whether the source is admissible at all. Everything shared between
source types — the dedup gate, ``CrawlTarget`` creation, log-dir routing and
enqueueing the fetch stage — stays in the actor, so a strategy is small and
side-effect free.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from backend.shared.clients.queue.validate_source_payload import ValidateSourcePayload
from backend.shared.models import ValidateSourceSettings
from backend.shared.storage.sql.sql_store import SqlStore


@dataclass(frozen=True)
class ValidationStrategyConfig:
    """Static description of a validation strategy plugin.

    ``name`` is the dataset ``source_type`` the strategy serves ("web" /
    "local") and the key it is looked up under in the registry.
    """

    name: str
    label: str
    description: str


@dataclass(frozen=True)
class NormalizedSource:
    """Canonical identity of one source, as computed by a strategy.

    ``original_url`` is what gets stored on ``CrawlTarget.original_url`` (the
    raw URL for web sources, the resolved absolute path for local files);
    ``normalized_url`` is the dedup key (normalized URL / ``file://`` URL).
    """

    original_url: str
    normalized_url: str


class SourceValidationError(Exception):
    """Raised by a strategy to reject a source before a target is created.

    ``reason`` is a short machine-readable token (e.g. ``"url_not_allowed"``,
    ``"file_not_found"``) used for skip logging.
    """

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(detail or reason)
        self.reason = reason


class SourceValidationStrategy(ABC):
    """Base class every validate_source strategy plugin subclasses."""

    config: ClassVar[ValidationStrategyConfig]

    @abstractmethod
    def normalize(
        self, *, payload: ValidateSourcePayload, settings: ValidateSourceSettings
    ) -> NormalizedSource:
        """Compute the source's canonical original/normalized identity."""
        raise NotImplementedError

    @abstractmethod
    def validate(
        self,
        *,
        payload: ValidateSourcePayload,
        source: NormalizedSource,
        store: SqlStore,
    ) -> None:
        """Raise :class:`SourceValidationError` when the source is rejected."""
        raise NotImplementedError
