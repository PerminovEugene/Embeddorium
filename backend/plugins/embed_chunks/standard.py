"""Standard embed strategy: provider-snapshot → (provider, model, mock_dim).

Carries over the ``embed_chunks`` launcher's previous provider parsing
verbatim: read ``provider_type`` from the stored snapshot and map it to the
worker-facing provider key, falling back to env defaults for the model name and
(mock) dimension. An ``ollama`` snapshot loads the configured Ollama model, a
``mock`` snapshot uses random vectors of ``mock_dim`` (defaulting to the env
``MOCK_EMBED_DIM``), and anything else is treated as a local HuggingFace model.
"""

from __future__ import annotations

from backend.plugins._fields import FieldSpec
from backend.plugins.embed_chunks.base import (
    EmbedStrategy,
    EmbedStrategyConfig,
    ResolvedProvider,
)
from backend.shared import config

# Kept identical to the launcher's previous inline default so runs whose
# snapshot omits a model name resolve to the same local model as before.
_HUGGINGFACE_DEFAULT_MODEL = "Qwen/Qwen3-Embedding-8B"


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
        model_name = snap.get("model_name") or snap.get("model")

        if provider_type == "ollama":
            return ResolvedProvider(
                provider="ollama",
                model=model_name or config.OLLAMA_EMBED_MODEL,
            )
        if provider_type == "mock":
            return ResolvedProvider(
                provider="mock",
                model="mock",
                mock_dim=snap.get("mock_dim", config.MOCK_EMBED_DIM),
            )
        # Remote provider or unknown → treat as huggingface/external.
        return ResolvedProvider(
            provider="huggingface",
            model=model_name or _HUGGINGFACE_DEFAULT_MODEL,
        )
