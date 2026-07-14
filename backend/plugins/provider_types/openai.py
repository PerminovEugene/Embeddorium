"""OpenAI (and OpenAI-compatible) provider-type adapter: a remote HTTP API.

A networked, authenticated endpoint: ``url`` defaults to the public OpenAI API
(env-overridable) and ``api_key`` is a real, if optional, credential. Adding a
sibling remote API later (e.g. ``claude.py``) is just another module like this
one.

The resolved target routes to the shared OpenAI HTTP embedding client. The
client is deliberately transport-only; configuration and endpoint assembly
remain in this adapter.
"""

from __future__ import annotations

from backend.plugins.provider_types._remote import (
    api_key_field,
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
)

_OPENAI_DEFAULT_MODEL = "text-embedding-3-small"


class OpenAIProviderType(ProviderTypeAdapter):
    config = ProviderTypeConfig(
        name="openai",
        label="OpenAI",
        description=(
            "A remote OpenAI-compatible embeddings API reached over HTTP with "
            "an API key."
        ),
        type="remote",
        supported_model_types=("embedding", "text", "long-text", "reranker"),
        fields=[
            url_field(
                default=env_default(
                    "OPENAI_BASE_URL",
                    "https://api.openai.com/v1",
                )
            ),
            port_field(default=None),
            api_key_field(),
            model_name_field(default=_OPENAI_DEFAULT_MODEL),
        ],
    )

    def resolve(self) -> ResolvedEmbedTarget:
        return ResolvedEmbedTarget(
            provider="openai",
            model=self._get("model_name") or _OPENAI_DEFAULT_MODEL,
            base_url=build_base_url(self._get("url"), self._get("port")),
            api_key=self._get("api_key") or None,
        )
