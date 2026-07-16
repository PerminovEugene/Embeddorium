"""Mock embedding model type: random vectors of a fixed dimension.

The one setting is the vector ``mock_dim`` — it must match the collection the
run indexed into, so it is configurable rather than hardcoded (defaulting to the
global ``MOCK_EMBED_DIM``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.plugins._fields import FieldSpec
from backend.plugins.provider_types.base import (
    ModelTypeConfig,
    ModelTypeHandler,
    ResolvedEmbedTarget,
)
from backend.shared import config

if TYPE_CHECKING:
    from backend.shared.clients.embed_client import EmbedClient


class MockEmbedding(ModelTypeHandler):
    config = ModelTypeConfig(
        model_type="embedding",
        label="Embedding",
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

    def build_embed_client(self) -> EmbedClient:
        from backend.shared.clients.mock_embed_client import MockEmbedClient

        return MockEmbedClient(self.resolve().mock_dim)
