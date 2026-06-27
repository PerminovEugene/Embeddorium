"""get_model_and_size() provider selection — kept separate from
test_embed_chunks_actor.py since it exercises module-level singleton state
(_model/_model_size) rather than the pure embed_chunks() logic.
"""

from unittest.mock import MagicMock, patch

import pytest

import laws_agent.actors.embed_chunks_actor.handler as handler_module
from laws_agent.actors.embed_chunks_actor.handler import get_model_and_size


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Each test selects its own provider — never reuse the cached model."""
    handler_module._model = None
    handler_module._model_size = None
    yield
    handler_module._model = None
    handler_module._model_size = None


def test_mock_provider_returns_mock_embed_client() -> None:
    with (
        patch.object(handler_module.config, "EMBED_PROVIDER", "mock"),
        patch.object(handler_module.config, "MOCK_EMBED_DIM", 8),
    ):
        model, size = get_model_and_size()

    assert size == 8
    assert model.get_embedding_dimension() == 8


def test_ollama_provider_builds_ollama_embed_client_with_configured_model_url() -> None:
    mock_client = MagicMock()
    mock_client.get_embedding_dimension.return_value = 1024
    mock_cls = MagicMock(return_value=mock_client)

    with (
        patch.object(handler_module.config, "EMBED_PROVIDER", "ollama"),
        patch.object(handler_module.config, "OLLAMA_EMBED_MODEL", "qwen3-embedding"),
        patch.object(handler_module.config, "OLLAMA_EMBED_BASE_URL", "http://ollama:11434"),
        patch("laws_agent.clients.ollama_embed_client.OllamaEmbedClient", mock_cls),
    ):
        model, size = get_model_and_size()

    mock_cls.assert_called_once_with(
        model="qwen3-embedding", base_url="http://ollama:11434"
    )
    assert model is mock_client
    assert size == 1024


def test_model_and_size_are_cached_as_module_singletons() -> None:
    with (
        patch.object(handler_module.config, "EMBED_PROVIDER", "mock"),
        patch.object(handler_module.config, "MOCK_EMBED_DIM", 4),
    ):
        first_model, first_size = get_model_and_size()
        second_model, second_size = get_model_and_size()

    assert first_model is second_model
    assert first_size == second_size == 4
