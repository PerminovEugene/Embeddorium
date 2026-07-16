"""Ollama provider type: a local (or LAN) Ollama server over HTTP.

Networked but usually local: the ``url``/``port`` defaults point at a loopback
Ollama and are env-sourced (``OLLAMA_URL`` / ``OLLAMA_PORT``) so a container or a
different host can override them without editing this file. No API key — Ollama
is unauthenticated. The model to run is a capability-specific setting, so it lives
on the model-type handlers under ``model_types/``.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from backend.plugins.provider_types._remote import (
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
from backend.shared import config


def _endpoint_defaults() -> tuple[str, int]:
    """Split the env-backed Ollama base URL into form-friendly URL and port."""
    parsed = urlsplit(config.OLLAMA_EMBED_BASE_URL)
    port = parsed.port or 11434
    host = parsed.hostname or "localhost"
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    url = urlunsplit((parsed.scheme or "http", host, parsed.path, "", ""))
    return url.rstrip("/"), port


_OLLAMA_URL, _OLLAMA_PORT = _endpoint_defaults()


class OllamaProviderType(ProviderTypeAdapter):
    config = ProviderTypeConfig(
        name="ollama",
        label="Ollama",
        description=(
            "A local or LAN Ollama server reached over HTTP. Pulls and runs "
            "the named model; no API key required. Serves embedding models and, "
            "when pointed at a rerank server, cross-encoder reranking."
        ),
        type="remote",
        fields=[
            url_field(default=env_default("OLLAMA_URL", _OLLAMA_URL)),
            port_field(default=int(env_default("OLLAMA_PORT", str(_OLLAMA_PORT)))),
        ],
    )

    def resolve_connection(self) -> ResolvedConnection:
        return ResolvedConnection(
            base_url=build_base_url(self._get("url"), self._get("port")),
        )
