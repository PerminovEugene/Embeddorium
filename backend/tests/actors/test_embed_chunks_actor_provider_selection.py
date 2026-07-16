"""get_embed_client_and_size() provider selection.

Kept separate from test_embed_chunks_actor.py since it exercises module-level
cache state (_clients) rather than the pure embed_chunks() logic. The actor is
provider-agnostic: it delegates client construction to the provider-type adapter
registry, so these tests assert the delegation and the caching, not a switch.
"""

from unittest.mock import MagicMock, patch

import pytest

import backend.actors.embed_chunks_actor.handler as handler_module
from backend.actors.embed_chunks_actor.handler import get_embed_client_and_size
from backend.shared.clients.mock_embed_client import MockEmbedClient


@pytest.fixture(autouse=True)
def _reset_cache():
    """Each test selects its own provider — never reuse a cached client."""
    handler_module._clients.clear()
    yield
    handler_module._clients.clear()


def test_mock_provider_builds_mock_client_with_configured_dim() -> None:
    client, size = get_embed_client_and_size("mock", "embedding", {"mock_dim": 8})

    assert isinstance(client, MockEmbedClient)
    assert size == 8
    assert client.get_embedding_dimension() == 8


def test_delegates_client_construction_to_the_registry() -> None:
    fake_client = MagicMock()
    fake_client.get_embedding_dimension.return_value = 1024

    with patch.object(
        handler_module, "build_embed_client", return_value=fake_client
    ) as build:
        client, size = get_embed_client_and_size(
            "ollama", "embedding", {"model_name": "qwen3-embedding"}
        )

    build.assert_called_once_with(
        "ollama", "embedding", {"model_name": "qwen3-embedding"}
    )
    assert client is fake_client
    assert size == 1024


def test_client_and_size_are_cached_by_provider_and_config() -> None:
    fake_client = MagicMock()
    fake_client.get_embedding_dimension.return_value = 4

    with patch.object(
        handler_module, "build_embed_client", return_value=fake_client
    ) as build:
        first_client, first_size = get_embed_client_and_size(
            "mock", "embedding", {"mock_dim": 4}
        )
        second_client, second_size = get_embed_client_and_size(
            "mock", "embedding", {"mock_dim": 4}
        )

    # Built and probed exactly once, then served from the cache.
    build.assert_called_once()
    fake_client.get_embedding_dimension.assert_called_once()
    assert first_client is second_client
    assert first_size == second_size == 4


def test_distinct_configs_build_distinct_clients() -> None:
    with patch.object(
        handler_module,
        "build_embed_client",
        side_effect=lambda pt, mt, cfg: MagicMock(
            get_embedding_dimension=MagicMock(return_value=cfg["mock_dim"])
        ),
    ) as build:
        _, size_a = get_embed_client_and_size("mock", "embedding", {"mock_dim": 4})
        _, size_b = get_embed_client_and_size("mock", "embedding", {"mock_dim": 8})

    assert build.call_count == 2
    assert size_a == 4
    assert size_b == 8
