import pytest

from laws_agent.clients.http.failures import FailureKind, classify_status


@pytest.mark.parametrize("status", [404, 410, 400, 401, 403])
def test_4xx_is_permanent(status):
    assert classify_status(status) is FailureKind.PERMANENT


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_retryable_statuses_are_transient(status):
    assert classify_status(status) is FailureKind.TRANSIENT
