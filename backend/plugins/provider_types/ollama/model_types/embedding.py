"""Ollama embedding model type: pull and run a named embedding model.

Uses the provider's resolved connection (``base_url``) and its own ``model_name``
to build the shared Ollama embed client (imported lazily).
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

# Pre-fills the form, and backs resolve() for a provider row that recorded an
# empty model_name. The model must exist on the target Ollama server.
_DEFAULT_MODEL = "qwen3-embedding"


class OllamaEmbedding(ModelTypeHandler):
    config = ModelTypeConfig(
        model_type="embedding",
        label="Embedding",
        fields=[model_name_field(default=_DEFAULT_MODEL)],
    )

    def resolve(self) -> ResolvedEmbedTarget:
        return ResolvedEmbedTarget(
            provider="ollama",
            model=self._get("model_name") or _DEFAULT_MODEL,
            base_url=self.connection.base_url,
        )

    def build_embed_client(self) -> EmbedClient:
        # Deferred import: pulls langchain_ollama/ollama only on this path.
        from backend.shared.clients.ollama_embed_client import OllamaEmbedClient

        target = self.resolve()
        return OllamaEmbedClient(model=target.model, base_url=target.base_url)
