"""Unit tests for the ``topK`` search parameter parsing."""

import pytest

from backend.server.search.service import DEFAULT_TOP_K, parse_top_k


@pytest.mark.parametrize("value", [None, ""])
def test_missing_top_k_falls_back_to_default(value):
    assert parse_top_k(value) == DEFAULT_TOP_K


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1, 1), (25, 25), ("10", 10), ("3", 3)],
)
def test_valid_top_k_is_coerced_to_int(value, expected):
    assert parse_top_k(value) == expected


@pytest.mark.parametrize("value", [0, -1, "0", "-5", "abc", "1.5", 2.7, [], {}])
def test_invalid_top_k_returns_none(value):
    assert parse_top_k(value) is None
