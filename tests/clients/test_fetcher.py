from unittest.mock import MagicMock

import pytest
from requests import exceptions as rex

from laws_agent.clients.http.failures import FailureKind, FetchFailure
from laws_agent.clients.http.fetcher import HttpFetcher


class _FakeResponse:
    def __init__(self, *, status_code=200, content_type="text/html", text="<html/>", url="https://emta.ee/", history=None, content_length=None):
        self.status_code = status_code
        self.headers = {}
        if content_type is not None:
            self.headers["Content-Type"] = content_type
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)
        self.text = text
        self.url = url
        self.history = history or []


def _fetcher(response=None, error=None, **kw):
    http_get = MagicMock()
    if error is not None:
        http_get.side_effect = error
    else:
        http_get.return_value = response or _FakeResponse()
    return HttpFetcher(http_get=http_get, **kw), http_get


def test_successful_fetch_returns_result():
    fetcher, http_get = _fetcher(
        _FakeResponse(
            content_type="text/html; charset=utf-8",
            text="<html>hi</html>",
            url="https://emta.ee/final",
            history=[MagicMock(url="https://emta.ee")],
        )
    )

    result = fetcher.fetch("https://emta.ee")

    assert result.status_code == 200
    assert result.content_type == "text/html; charset=utf-8"
    assert result.content == "<html>hi</html>"
    assert result.final_url == "https://emta.ee/final"
    assert result.redirect_chain == ["https://emta.ee"]
    # TLS verification on by default.
    assert http_get.call_args.kwargs["verify"] is True


def test_allow_insecure_tls_disables_verify():
    fetcher, http_get = _fetcher()
    fetcher.fetch("https://emta.ee", allow_insecure_tls=True)
    assert http_get.call_args.kwargs["verify"] is False


def test_404_is_permanent():
    fetcher, _ = _fetcher(_FakeResponse(status_code=404))
    with pytest.raises(FetchFailure) as exc:
        fetcher.fetch("https://emta.ee")
    assert exc.value.kind is FailureKind.PERMANENT
    assert exc.value.status == 404


def test_503_is_transient():
    fetcher, _ = _fetcher(_FakeResponse(status_code=503))
    with pytest.raises(FetchFailure) as exc:
        fetcher.fetch("https://emta.ee")
    assert exc.value.kind is FailureKind.TRANSIENT


def test_timeout_is_transient():
    fetcher, _ = _fetcher(error=rex.Timeout("slow"))
    with pytest.raises(FetchFailure) as exc:
        fetcher.fetch("https://emta.ee")
    assert exc.value.kind is FailureKind.TRANSIENT


def test_ssl_error_is_permanent():
    fetcher, _ = _fetcher(error=rex.SSLError("bad cert"))
    with pytest.raises(FetchFailure) as exc:
        fetcher.fetch("https://emta.ee")
    assert exc.value.kind is FailureKind.PERMANENT


def test_oversized_content_is_permanent():
    fetcher, _ = _fetcher(
        _FakeResponse(content_length=100), max_bytes=10
    )
    with pytest.raises(FetchFailure) as exc:
        fetcher.fetch("https://emta.ee")
    assert exc.value.kind is FailureKind.PERMANENT
