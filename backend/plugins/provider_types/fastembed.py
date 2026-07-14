"""FastEmbed provider-type adapter: a local ONNX embedding model, in-process.

FastEmbed downloads an ONNX model and computes vectors via onnxruntime — no
server, port, or API key, so ``model_name`` is the only setting it needs. The
heavy onnxruntime import happens lazily in the embed client the target resolves
to, never here.
"""

from __future__ import annotations

from backend.plugins._fields import FieldSpec
from backend.plugins.provider_types.base import (
    ProviderTypeAdapter,
    ProviderTypeConfig,
    ResolvedEmbedTarget,
)

# FastEmbed's small, fast default model when a config omits a model name.
_FASTEMBED_DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class FastembedProviderType(ProviderTypeAdapter):
    config = ProviderTypeConfig(
        name="fastembed",
        label="FastEmbed (local)",
        description=(
            "Runs a local ONNX embedding model in-process via Qdrant's "
            "FastEmbed library — no server, port, or API key."
        ),
        type="builtin",
        supported_model_types=("embedding",),
        fields=[
            FieldSpec(
                key="model_name",
                label="Model",
                type="text",
                default=_FASTEMBED_DEFAULT_MODEL,
                placeholder=_FASTEMBED_DEFAULT_MODEL,
                required=True,
            ),
        ],
    )

    def resolve(self) -> ResolvedEmbedTarget:
        return ResolvedEmbedTarget(
            provider="fastembed",
            model=self._get("model_name") or _FASTEMBED_DEFAULT_MODEL,
        )
