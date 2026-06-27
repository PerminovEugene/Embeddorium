from unittest.mock import MagicMock, patch

import numpy as np

from laws_agent.clients.ollama_embed_client import OllamaEmbedClient


def _make_client(**kwargs) -> OllamaEmbedClient:
    with patch("laws_agent.clients.ollama_embed_client.OllamaEmbeddings"):
        return OllamaEmbedClient(
            model=kwargs.get("model", "qwen3-embedding"),
            base_url=kwargs.get("base_url", "http://ollama:11434"),
        )


def test_constructs_ollama_embeddings_with_model_and_base_url() -> None:
    with patch("laws_agent.clients.ollama_embed_client.OllamaEmbeddings") as mock_cls:
        OllamaEmbedClient(model="qwen3-embedding", base_url="http://ollama:11434")

    mock_cls.assert_called_once_with(
        model="qwen3-embedding", base_url="http://ollama:11434"
    )


def test_encode_returns_array_with_one_row_per_sentence() -> None:
    client = _make_client()
    client._client.embed_documents = MagicMock(
        return_value=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    )

    embeddings = client.encode(["a", "b", "c"])

    assert embeddings.shape == (3, 2)
    client._client.embed_documents.assert_called_once_with(["a", "b", "c"])


def test_encode_supports_tolist_like_sentence_transformer_output() -> None:
    client = _make_client()
    client._client.embed_documents = MagicMock(return_value=[[1.0, 2.0, 3.0]])

    embeddings = client.encode(["only one"])
    vector = embeddings[0].tolist()

    assert isinstance(vector, list)
    assert vector == [1.0, 2.0, 3.0]


def test_normalize_embeddings_produces_unit_vectors() -> None:
    client = _make_client()
    client._client.embed_documents = MagicMock(return_value=[[3.0, 4.0], [1.0, 0.0]])

    embeddings = client.encode(["x", "y"], normalize_embeddings=True)
    norms = np.linalg.norm(embeddings, axis=1)

    np.testing.assert_allclose(norms, 1.0, rtol=1e-6)


def test_without_normalization_vectors_are_unchanged() -> None:
    client = _make_client()
    client._client.embed_documents = MagicMock(return_value=[[3.0, 4.0]])

    embeddings = client.encode(["x"], normalize_embeddings=False)

    np.testing.assert_allclose(embeddings, [[3.0, 4.0]])


def test_get_embedding_dimension_probes_server_once_and_caches() -> None:
    client = _make_client()
    client._client.embed_query = MagicMock(return_value=[0.0] * 1024)

    first = client.get_embedding_dimension()
    second = client.get_embedding_dimension()

    assert first == 1024
    assert second == 1024
    client._client.embed_query.assert_called_once()
