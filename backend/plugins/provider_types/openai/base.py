"""OpenAI (and OpenAI-compatible) provider type: a remote HTTP API.

A networked, authenticated endpoint: ``url`` defaults to the public OpenAI API
(env-overridable) and ``api_key`` is a real, if optional, credential. Adding a
sibling remote API later (e.g. an ``anthropic`` folder) is just another provider
package like this one. The model to call is capability-specific and lives on the
model-type handlers under ``model_types/``.
"""

from __future__ import annotations

from backend.plugins.provider_types._remote import (
    api_key_field,
    build_base_url,
    env_default,
    port_field,
    url_field,
)
from backend.plugins.provider_types.base import (
    ProviderTypeAdapter,
    ProviderTypeConfig,
    ResolvedConnection,
)


class OpenAIProviderType(ProviderTypeAdapter):
    config = ProviderTypeConfig(
        name="openai",
        label="OpenAI",
        description=(
            "A remote OpenAI-compatible embeddings API reached over HTTP with "
            "an API key."
        ),
        type="remote",
        fields=[
            url_field(
                default=env_default(
                    "OPENAI_BASE_URL",
                    "https://api.openai.com/v1",
                )
            ),
            port_field(default=None),
            api_key_field(),
        ],
    )

    def resolve_connection(self) -> ResolvedConnection:
        return ResolvedConnection(
            base_url=build_base_url(self._get("url"), self._get("port")),
            api_key=self._get("api_key") or None,
        )
