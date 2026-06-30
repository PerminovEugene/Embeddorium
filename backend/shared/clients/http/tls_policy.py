"""Explicit, domain-scoped TLS relaxation.

TLS verification is the default. A site with broken TLS is opted in by adding
its host to ``INSECURE_TLS_DOMAINS`` (env / config) — never globally.
"""

from __future__ import annotations

from typing import Iterable, Optional
from urllib.parse import urlparse

from backend.shared import config


def allow_insecure_tls(url: str, allowed_domains: Optional[Iterable[str]] = None) -> bool:
    domains = (
        config.INSECURE_TLS_DOMAINS
        if allowed_domains is None
        else frozenset(d.lower() for d in allowed_domains)
    )
    host = (urlparse(url).hostname or "").lower()
    return host in domains
