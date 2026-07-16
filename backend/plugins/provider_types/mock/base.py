"""Mock provider type: random vectors, no model, no network.

Used for fast pipeline dry runs and tests. It has no connection to configure —
the only setting (the vector ``mock_dim``) is capability-specific and lives on
the embedding model-type handler under ``model_types/``.
"""

from __future__ import annotations

from backend.plugins.provider_types.base import (
    ProviderTypeAdapter,
    ProviderTypeConfig,
    ResolvedConnection,
)


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
        fields=[],
    )

    def resolve_connection(self) -> ResolvedConnection:
        # In-process: there is nothing to connect to.
        return ResolvedConnection()
