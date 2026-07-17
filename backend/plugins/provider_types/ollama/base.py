"""Ollama provider type: a local (or LAN) Ollama server over HTTP.

Networked but usually local: the ``url``/``port`` defaults point at a loopback
Ollama and are env-sourced (``OLLAMA_URL`` / ``OLLAMA_PORT``) so a container or a
different host can override them without editing this file. No API key — Ollama
is unauthenticated. The model to run is a capability-specific setting, so it lives
on the model-type handlers under ``model_types/``.

These are only *form defaults*; the endpoint a run actually uses is whatever the
provider row recorded. The default matters when the form is filled from inside a
container, where ``http://localhost`` is the container's own loopback and not the
host — set ``OLLAMA_URL`` to ``http://ollama`` (Ollama as a compose service,
profile "ollama") or ``http://host.docker.internal`` (Ollama on the host,
Mac/Windows Docker Desktop).
"""

from __future__ import annotations

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

_DEFAULT_URL = "http://localhost"
_DEFAULT_PORT = "11434"


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
            url_field(default=env_default("OLLAMA_URL", _DEFAULT_URL)),
            port_field(default=int(env_default("OLLAMA_PORT", _DEFAULT_PORT))),
        ],
    )

    def resolve_connection(self) -> ResolvedConnection:
        return ResolvedConnection(
            base_url=build_base_url(self._get("url"), self._get("port")),
        )
