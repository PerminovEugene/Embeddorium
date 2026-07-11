"""The embed_chunks strategy plugin interface.

An embed strategy owns the provider-specific half of the ``embed_chunks``
actor: turning a run's stored embedding-provider snapshot
(:attr:`~backend.shared.models.pipeline_run.EmbedChunksSettings.provider`) into
the concrete ``(provider, model, mock_dim)`` triple the worker needs to load a
model. Everything else — the model cache, the encode loop, vector upsert,
marking chunks embedded, finalizing the target and the run-progress counters —
stays in the actor/launcher, since it is provider-agnostic plumbing.

The single built-in strategy (``standard``) reproduces the launcher's previous
provider-snapshot parsing exactly: ``ollama``/``mock`` are recognised by
``provider_type`` (falling back to env defaults for model/dim), and any other
snapshot is treated as a local HuggingFace model.

Its one configurable field is of type ``"provider_id"``: the UI renders a
picker over the configured embedding :class:`~backend.shared.models.provider.
Provider` records, and run-creation stores the picked provider's snapshot under
``EmbedChunksSettings.provider`` (the ``provider`` key).

Subclasses set a class-level ``config`` (an :class:`EmbedStrategyConfig`) and
implement :meth:`resolve`. ``__init__`` resolves the raw ``settings`` dict
against ``config.fields`` with per-field defaults — the same settings-
resolution convenience the chunker plugins offer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from backend.plugins._fields import FieldSpec


@dataclass(frozen=True)
class EmbedStrategyConfig:
    """Static, UI-facing description of an embed strategy plugin.

    ``name`` is the stable id the strategy is looked up under in the registry;
    ``fields`` describes the knobs the actor reads out of
    :class:`~backend.shared.models.pipeline_run.EmbedChunksSettings`, served
    camelCased like every other plugin config.
    """

    name: str
    label: str
    description: str
    fields: list[FieldSpec] = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedProvider:
    """The concrete embedding target derived from a provider snapshot.

    ``provider`` is the worker-facing provider key (``"ollama"`` / ``"mock"`` /
    ``"huggingface"``); ``model`` is the model name to load; ``mock_dim`` is the
    vector size for the mock provider (``None`` for real providers).
    """

    provider: str
    model: str
    mock_dim: int | None = None


class EmbedStrategy(ABC):
    """Base class every embed_chunks strategy plugin subclasses."""

    config: ClassVar[EmbedStrategyConfig]

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        settings = settings or {}
        self.settings: dict[str, Any] = {
            f.key: settings.get(f.key, f.default) for f in self.config.fields
        }

    def _get(self, key: str) -> Any:
        """Return the resolved value for a declared field key."""
        return self.settings[key]

    @abstractmethod
    def resolve(self) -> ResolvedProvider:
        """Resolve the run's provider snapshot into a concrete embed target."""
        raise NotImplementedError
