"""Cross-encoder reranker model type: a reranker served over HTTP.

A cross-encoder scores ``(query, candidate)`` pairs jointly rather than producing
an embedding, so it serves the ``cross-encoder`` capability and is consumed by
the reranking half of hybrid search rather than by the embed_chunks actor. It is
a *model type*, not a provider type: it is offered under the ``ollama`` provider,
whose ``url``/``port`` connection points at the rerank server.

The model runs as a *networked* service, not in-process: the backend runs in
Docker and must keep torch/sentence-transformers out of the container image, so —
exactly like the embedding models — the reranker is reached over HTTP. The
canonical way to serve a Qwen3/BGE reranker with calibrated scores is a **vLLM**
server, which exposes an OpenAI/Jina/Cohere-style rerank endpoint
(``POST /v1/rerank`` → ``{"results": [{"index", "relevance_score"}, ...]}``); TEI,
Infinity and Cohere/Jina speak the same contract. So the provider's connection is
pointed at that server (e.g. ``http://localhost:8000``) and this handler owns the
``model_name`` and the ``rerank_path`` (servers disagree: vLLM ``v1/rerank``,
Infinity ``rerank``).
"""

from __future__ import annotations

from backend.plugins._fields import FieldSpec
from backend.plugins.provider_types._remote import env_default, model_name_field
from backend.plugins.provider_types.base import (
    ModelTypeConfig,
    ModelTypeHandler,
    ResolvedRerankTarget,
)

# A common reranker model tag; the default when a config omits a model name. The
# user serves their own on the rerank host, so this is only a hint/placeholder.
_CROSS_ENCODER_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"

# Rerank endpoint path relative to the server URL. Servers disagree — vLLM serves
# the OpenAI-compatible ``v1/rerank``, Infinity serves ``rerank`` — so it is a
# per-model-type field rather than a client constant. Env-overridable for the
# default so a deployment can set its house standard once.
_DEFAULT_RERANK_PATH = env_default("RERANKER_PATH", "v1/rerank")


class OllamaCrossEncoder(ModelTypeHandler):
    config = ModelTypeConfig(
        model_type="cross-encoder",
        label="Cross-Encoder reranker (HTTP)",
        fields=[
            model_name_field(default=_CROSS_ENCODER_DEFAULT_MODEL),
            FieldSpec(
                key="rerank_path",
                label="Rerank endpoint path",
                type="text",
                default=_DEFAULT_RERANK_PATH,
                placeholder="v1/rerank (vLLM) | rerank (Infinity)",
                required=True,
            ),
        ],
    )

    def resolve_rerank(self) -> ResolvedRerankTarget:
        return ResolvedRerankTarget(
            provider="http_rerank",
            model=self._get("model_name") or _CROSS_ENCODER_DEFAULT_MODEL,
            base_url=self.connection.base_url,
            path=(self._get("rerank_path") or _DEFAULT_RERANK_PATH).lstrip("/"),
        )
