import numpy as np

from backend.shared.clients.mock_embed_client import MockEmbedClient


def test_encode_returns_one_row_per_sentence_with_configured_dimension() -> None:
    client = MockEmbedClient(dimension=8, seed=0)
    embeddings = client.encode(["a", "b", "c"], batch_size=2)

    assert embeddings.shape == (3, 8)


def test_encode_rows_support_tolist_like_sentence_transformer_output() -> None:
    client = MockEmbedClient(dimension=4, seed=0)
    embeddings = client.encode(["only one"])

    vector = embeddings[0].tolist()
    assert isinstance(vector, list)
    assert len(vector) == 4


def test_normalize_embeddings_produces_unit_vectors() -> None:
    client = MockEmbedClient(dimension=16, seed=0)
    embeddings = client.encode(["x", "y"], normalize_embeddings=True)

    norms = np.linalg.norm(embeddings, axis=1)
    np.testing.assert_allclose(norms, 1.0, rtol=1e-6)


def test_without_normalization_vectors_are_not_unit_length() -> None:
    client = MockEmbedClient(dimension=16, seed=0)
    embeddings = client.encode(["x", "y"], normalize_embeddings=False)

    norms = np.linalg.norm(embeddings, axis=1)
    assert not np.allclose(norms, 1.0)


def test_seeded_client_is_deterministic() -> None:
    first = MockEmbedClient(dimension=8, seed=42).encode(["same input"])
    second = MockEmbedClient(dimension=8, seed=42).encode(["same input"])

    np.testing.assert_array_equal(first, second)


def test_unseeded_clients_produce_different_vectors() -> None:
    first = MockEmbedClient(dimension=8).encode(["same input"])
    second = MockEmbedClient(dimension=8).encode(["same input"])

    assert not np.array_equal(first, second)


def test_get_embedding_dimension_matches_constructor_argument() -> None:
    client = MockEmbedClient(dimension=4096)
    assert client.get_embedding_dimension() == 4096
