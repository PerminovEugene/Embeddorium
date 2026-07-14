"""Shared helpers for networked (``type="remote"``) provider-type adapters.

Underscore-prefixed so plugin discovery skips it (see
``backend.plugins._strategy_discovery``). Ollama, OpenAI and any future remote
API adapter (e.g. ``claude.py``) reuse the ``url``/``port``/``api_key`` field
descriptors and the ``base_url`` assembly here, so a new remote provider type is
a few lines plus its worker-key mapping.
"""

from __future__ import annotations

import os

from backend.plugins._fields import FieldSpec


def url_field(default: str) -> FieldSpec:
    """A required endpoint-URL field (scheme + host, no port)."""
    return FieldSpec(
        key="url",
        label="URL",
        type="text",
        default=default,
        placeholder=default,
        required=True,
    )


def port_field(default: int | None) -> FieldSpec:
    """An optional port field; ``None`` default means the URL carries the port."""
    return FieldSpec(
        key="port",
        label="Port",
        type="number",
        default=default,
        min=1,
        max=65535,
    )


def api_key_field() -> FieldSpec:
    """An optional API-key field — only meaningful for authenticated APIs."""
    return FieldSpec(
        key="api_key",
        label="API key",
        type="text",
        default="",
        placeholder="sk-...",
        required=False,
    )


def model_name_field(default: str) -> FieldSpec:
    return FieldSpec(
        key="model_name",
        label="Model",
        type="text",
        default=default,
        placeholder=default,
        required=True,
    )


def env_default(name: str, fallback: str) -> str:
    """Env-sourced default for a field, falling back to *fallback*."""
    return os.getenv(name, fallback)


def build_base_url(url: str | None, port: int | None) -> str | None:
    """Join a ``url`` and optional ``port`` into a single endpoint.

    ``"http://localhost"`` + ``11434`` -> ``"http://localhost:11434"``; a falsy
    ``port`` leaves the URL untouched (the URL already carries the port, or the
    API is a plain hostname).
    """
    url = (url or "").rstrip("/")
    if not url:
        return None
    if not port:
        return url

    # Do not append a second port when the configured URL already carries one.
    from urllib.parse import urlsplit, urlunsplit

    parsed = urlsplit(url)
    if parsed.port is not None:
        return url
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = f"{host}:{port}"
    if parsed.username:
        credentials = parsed.username
        if parsed.password:
            credentials += f":{parsed.password}"
        netloc = f"{credentials}@{netloc}"
    return urlunsplit(
        (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)
    )
