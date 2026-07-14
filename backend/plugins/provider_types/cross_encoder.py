"""Cross-encoder provider-type adapter: a reranker served over HTTP.

A cross-encoder scores ``(query, candidate)`` pairs jointly rather than
producing an embedding, so it serves the ``cross-encoder`` capability, not
``embedding``, and is consumed by the reranking half of hybrid search rather
than by the embed_chunks actor.

The model runs as a *networked* service, not in-process: the backend runs in
Docker and must keep torch/sentence-transformers out of the container image, so
— exactly like the embedding providers — the reranker is reached over HTTP. The
canonical way to serve a Qwen3/BGE reranker with calibrated scores is a **vLLM**
server, which exposes an OpenAI/Jina/Cohere-style rerank endpoint
(``POST /v1/rerank`` → ``{"results": [{"index", "relevance_score"}, ...]}``);
TEI, Infinity and Cohere/Jina speak the same contract. (Stock Ollama has no
rerank endpoint — it only serves ``/api/chat`` — so it is not a scoring backend
here.) That makes this a ``remote`` adapter with the usual ``url``/``port``/
``model_name`` connection fields, defaulting to a local vLLM endpoint.
"""

from __future__ import annotations

from backend.plugins._fields import FieldSpec
from backend.plugins.provider_types._remote import (
    build_base_url,
    env_default,
    model_name_field,
    port_field,
    url_field,
)
from backend.plugins.provider_types.base import (
    ProviderTypeAdapter,
    ProviderTypeConfig,
    ResolvedEmbedTarget,
    ResolvedRerankTarget,
)

# A common reranker model tag; the default when a config omits a model name. The
# user serves their own on the rerank host, so this is only a hint/placeholder.
_CROSS_ENCODER_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"

# A local vLLM rerank server's typical endpoint. Overridable via env so a
# container or a different host can point elsewhere without editing this file.
_DEFAULT_RERANK_URL = env_default("RERANKER_URL", "http://localhost")
_DEFAULT_RERANK_PORT = int(env_default("RERANKER_PORT", "8000"))

# Rerank endpoint path relative to the server URL. Servers disagree — vLLM
# serves the OpenAI-compatible ``v1/rerank``, Infinity serves ``rerank`` — so it
# is a per-provider field rather than a client constant. Env-overridable for the
# default so a deployment can set its house standard once.
_DEFAULT_RERANK_PATH = env_default("RERANKER_PATH", "v1/rerank")


class CrossEncoderProviderType(ProviderTypeAdapter):
    config = ProviderTypeConfig(
        name="cross_encoder",
        label="Cross-Encoder reranker (HTTP)",
        description=(
            "Re-scores (query, candidate) pairs with a cross-encoder reranker "
            "served over HTTP by a vLLM (or TEI/Infinity/Cohere-style) server "
            "exposing a /v1/rerank endpoint — no torch in the container. Used "
            "to rerank hybrid search results."
        ),
        type="remote",
        supported_model_types=("cross-encoder",),
        fields=[
            url_field(default=_DEFAULT_RERANK_URL),
            port_field(default=_DEFAULT_RERANK_PORT),
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

    def resolve(self) -> ResolvedEmbedTarget:
        # A cross-encoder is a reranker, not an embedder: it must never be
        # selected as an embed target. Fail loud rather than return a bogus one.
        raise NotImplementedError(
            "cross_encoder is a reranker, not an embedder; use resolve_rerank()"
        )

    def resolve_rerank(self) -> ResolvedRerankTarget:
        return ResolvedRerankTarget(
            provider="http_rerank",
            model=self._get("model_name") or _CROSS_ENCODER_DEFAULT_MODEL,
            base_url=build_base_url(self._get("url"), self._get("port")),
            path=(self._get("rerank_path") or _DEFAULT_RERANK_PATH).lstrip("/"),
        )
