"""Mock embedding model type: random vectors of a fixed dimension.

The one setting is the vector ``mock_dim`` — it must match the collection the
run indexed into, so it is a per-provider form field rather than a hardcoded
constant. The default below is only what the form is pre-filled with.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.plugins._fields import FieldSpec
from backend.plugins.provider_types.base import (
    ModelTypeConfig,
    ModelTypeHandler,
    ResolvedEmbedTarget,
)

if TYPE_CHECKING:
    from backend.shared.clients.embed_client import EmbedClient

# Qwen/Qwen3-Embedding-8B's dimension: defaulting to it keeps a mock run's
# collection compatible with one embedded by the real model, so the two can be
# swapped without rebuilding the vector store.
_DEFAULT_MOCK_DIM = 4096


class MockEmbedding(ModelTypeHandler):
    config = ModelTypeConfig(
        model_type="embedding",
        label="Embedding",
        fields=[
            FieldSpec(
                key="mock_dim",
                label="Vector dimension",
                type="number",
                default=_DEFAULT_MOCK_DIM,
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

    def build_embed_client(self) -> EmbedClient:
        from backend.shared.clients.mock_embed_client import MockEmbedClient

        return MockEmbedClient(self.resolve().mock_dim)
