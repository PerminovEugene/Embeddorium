"""Standard embed strategy: provider-snapshot → (provider, model, mock_dim).

Dispatches through the provider-type adapter registry instead of an inline
``if provider_type == ...`` chain: it reads the run's stored provider snapshot,
hands the snapshot's ``config`` to the matching
:class:`~backend.plugins.provider_types.base.ProviderTypeAdapter`, and adapts
that adapter's :class:`ResolvedEmbedTarget` into the ``(provider, model,
mock_dim)`` triple the launcher/worker expects. An unknown/legacy provider type
falls back to the local HuggingFace path (see
:func:`~backend.plugins.provider_types.registry.resolve_embed_target`).
"""

from __future__ import annotations

from backend.plugins._fields import FieldSpec
from backend.plugins.embed_chunks.base import (
    EmbedStrategy,
    EmbedStrategyConfig,
    ResolvedProvider,
)
from backend.plugins.provider_types.registry import resolve_embed_target


class StandardEmbed(EmbedStrategy):
    config = EmbedStrategyConfig(
        name="standard",
        label="Standard embedding",
        description=(
            "Embeds chunks with the selected provider's model and upserts the "
            "vectors into the run's collection."
        ),
        fields=[
            FieldSpec(
                key="provider",
                label="Embedding provider",
                type="provider_id",
                default=None,
                required=True,
            ),
        ],
    )

    def resolve(self) -> ResolvedProvider:
        snap = self._get("provider") or {}
        provider_type = snap.get("provider_type", "")
        # New snapshots nest type-specific settings under "config"; older/flat
        # snapshots keep them at the top level — accept both.
        values = snap.get("config") or snap

        target = resolve_embed_target(provider_type, values)
        return ResolvedProvider(
            provider=target.provider,
            model=target.model or "",
            mock_dim=target.mock_dim,
            base_url=target.base_url,
            api_key=target.api_key,
        )
