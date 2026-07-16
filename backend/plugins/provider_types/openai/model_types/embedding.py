"""OpenAI embedding model type: call a named embeddings model over HTTP.

The resolved target routes to the shared OpenAI HTTP embedding client, which is
deliberately transport-only; configuration and endpoint assembly stay here (the
provider's connection) and on this handler (the model).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.plugins.provider_types._remote import model_name_field
from backend.plugins.provider_types.base import (
    ModelTypeConfig,
    ModelTypeHandler,
    ResolvedEmbedTarget,
)

if TYPE_CHECKING:
    from backend.shared.clients.embed_client import EmbedClient

_OPENAI_DEFAULT_MODEL = "text-embedding-3-small"


class OpenAIEmbedding(ModelTypeHandler):
    config = ModelTypeConfig(
        model_type="embedding",
        label="Embedding",
        fields=[model_name_field(default=_OPENAI_DEFAULT_MODEL)],
    )

    def resolve(self) -> ResolvedEmbedTarget:
        return ResolvedEmbedTarget(
            provider="openai",
            model=self._get("model_name") or _OPENAI_DEFAULT_MODEL,
            base_url=self.connection.base_url,
            api_key=self.connection.api_key,
        )

    def build_embed_client(self) -> EmbedClient:
        from backend.shared.clients.openai_embed_client import OpenAIEmbedClient

        target = self.resolve()
        if not target.base_url:
            raise ValueError("openai provider requires a base_url")
        return OpenAIEmbedClient(
            model=target.model,
            base_url=target.base_url,
            api_key=target.api_key,
        )
