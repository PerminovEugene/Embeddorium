"""Mock provider-type adapter: random vectors, no model, no network.

Used for fast pipeline dry runs and tests. Its one setting is the vector
``mock_dim`` — it must match the collection the run indexed into, so it is
configurable rather than hardcoded (defaulting to the global ``MOCK_EMBED_DIM``).
"""

from __future__ import annotations

from backend.plugins._fields import FieldSpec
from backend.plugins.provider_types.base import (
    ProviderTypeAdapter,
    ProviderTypeConfig,
    ResolvedEmbedTarget,
)
from backend.shared import config


class MockProviderType(ProviderTypeAdapter):
    config = ProviderTypeConfig(
        name="mock",
        label="Mock",
        description=(
            "In-process provider that returns random vectors of a fixed "
            "dimension. No model load and no network — for fast dry runs and "
            "tests."
        ),
        type="builtin",
        supported_model_types=("embedding",),
        fields=[
            FieldSpec(
                key="mock_dim",
                label="Vector dimension",
                type="number",
                default=config.MOCK_EMBED_DIM,
                min=1,
            ),
        ],
    )

    def resolve(self) -> ResolvedEmbedTarget:
        return ResolvedEmbedTarget(
            provider="mock",
            model="mock",
            mock_dim=int(self._get("mock_dim")),
        )
