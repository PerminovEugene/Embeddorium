"""HTTP fetching abstraction used by the ``fetch_source`` actor.

Wraps a low-level ``http_get`` callable (``requests.get`` by default, but
injectable for tests) and turns the response into a typed :class:`FetchResult`,
raising :class:`FetchFailure` with an explicit transient/permanent kind. TLS
verification is ON by default and only relaxed when the caller explicitly opts
in for an allowlisted domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import requests
from requests import exceptions as rex

from laws_agent.clients.http.failures import (
    FailureKind,
    FetchFailure,
    classify_status,
)

DEFAULT_USER_AGENT = (
    "laws-agent-crawler/0.1 (+https://github.com/; legal/tax document ingestion)"
)
DEFAULT_TIMEOUT = (5, 30)  # (connect, read) seconds
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MiB


@dataclass(frozen=True)
class FetchResult:
    final_url: str
    status_code: int
    content_type: Optional[str]
    content: str
    redirect_chain: list[str] = field(default_factory=list)


class HttpFetcher:
    def __init__(
        self,
        *,
        http_get: Optional[Callable[..., object]] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: tuple[int, int] = DEFAULT_TIMEOUT,
        max_bytes: Optional[int] = DEFAULT_MAX_BYTES,
    ) -> None:
        self._http_get = http_get or requests.get
        self._user_agent = user_agent
        self._timeout = timeout
        self._max_bytes = max_bytes

    def fetch(self, url: str, *, allow_insecure_tls: bool = False) -> FetchResult:
        try:
            response = self._http_get(
                url,
                timeout=self._timeout,
                verify=not allow_insecure_tls,
                allow_redirects=True,
                headers={"User-Agent": self._user_agent},
            )
        except rex.SSLError as exc:
            raise FetchFailure(
                FailureKind.PERMANENT, f"ssl error: {exc}"
            ) from exc
        except (rex.Timeout, rex.ConnectionError) as exc:
            raise FetchFailure(
                FailureKind.TRANSIENT, f"connection error: {exc}"
            ) from exc
        except (rex.MissingSchema, rex.InvalidSchema, rex.InvalidURL, rex.TooManyRedirects) as exc:
            raise FetchFailure(
                FailureKind.PERMANENT, f"invalid request: {exc}"
            ) from exc
        except rex.RequestException as exc:
            # Unknown request error: be conservative and allow a retry.
            raise FetchFailure(
                FailureKind.TRANSIENT, f"request error: {exc}"
            ) from exc

        status = int(response.status_code)
        if status >= 400:
            raise FetchFailure(
                classify_status(status), f"http status {status}", status=status
            )

        content_type = response.headers.get("Content-Type")

        declared = response.headers.get("Content-Length")
        if self._max_bytes is not None and declared is not None:
            try:
                if int(declared) > self._max_bytes:
                    raise FetchFailure(
                        FailureKind.PERMANENT,
                        f"content too large: {declared} bytes",
                        status=status,
                    )
            except ValueError:
                pass

        content = response.text or ""
        if (
            self._max_bytes is not None
            and len(content.encode("utf-8", "ignore")) > self._max_bytes
        ):
            raise FetchFailure(
                FailureKind.PERMANENT,
                "content exceeds max size",
                status=status,
            )

        redirect_chain = [h.url for h in getattr(response, "history", []) or []]

        return FetchResult(
            final_url=getattr(response, "url", url),
            status_code=status,
            content_type=content_type,
            content=content,
            redirect_chain=redirect_chain,
        )
