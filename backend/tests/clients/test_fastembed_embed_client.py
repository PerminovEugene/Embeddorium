"""FastembedEmbedClient interface tests.

FastEmbed downloads a real ONNX model on first ``embed``, so these tests
monkeypatch ``fastembed.TextEmbedding`` with a tiny fake to stay fast and
offline — they exercise the client's adapter logic (dimension lookup,
normalization, empty input, positional alignment), not fastembed itself.
"""

from __future__ import annotations

import numpy as np
import pytest

import backend.shared.clients.fastembed_embed_client as fe_module
from backend.shared.clients.fastembed_embed_client import FastembedEmbedClient

_KNOWN_MODEL = "BAAI/bge-small-en-v1.5"
_KNOWN_DIM = 6


class _FakeTextEmbedding:
    """Stand-in for ``fastembed.TextEmbedding`` returning deterministic vectors."""

    def __init__(self, model_name: str = _KNOWN_MODEL, lazy_load: bool = False):
        self.model_name = model_name

    @classmethod
    def list_supported_models(cls):
        return [{"model": _KNOWN_MODEL, "dim": _KNOWN_DIM}]

    def embed(self, documents, batch_size: int = 256, **kwargs):
        for i, _ in enumerate(documents):
            # Non-unit vectors so normalization is observable.
            yield np.full(_KNOWN_DIM, float(i + 1), dtype=np.float32)


@pytest.fixture(autouse=True)
def _fake_fastembed(monkeypatch):
    import fastembed

    monkeypatch.setattr(fastembed, "TextEmbedding", _FakeTextEmbedding)
    yield


def test_get_embedding_dimension_read_from_metadata() -> None:
    client = FastembedEmbedClient(_KNOWN_MODEL)
    assert client.get_embedding_dimension() == _KNOWN_DIM


def test_default_model_is_used_when_none() -> None:
    client = FastembedEmbedClient(None)
    assert client.model == _KNOWN_MODEL


def test_encode_returns_one_row_per_sentence() -> None:
    client = FastembedEmbedClient(_KNOWN_MODEL)
    embeddings = client.encode(["a", "b", "c"])
    assert embeddings.shape == (3, _KNOWN_DIM)


def test_encode_empty_input_returns_empty_array() -> None:
    client = FastembedEmbedClient(_KNOWN_MODEL)
    embeddings = client.encode([])
    assert embeddings.shape == (0, 0)


def test_normalize_embeddings_produces_unit_vectors() -> None:
    client = FastembedEmbedClient(_KNOWN_MODEL)
    embeddings = client.encode(["x", "y"], normalize_embeddings=True)
    norms = np.linalg.norm(embeddings, axis=1)
    np.testing.assert_allclose(norms, 1.0, rtol=1e-6)


def test_without_normalization_vectors_are_not_unit_length() -> None:
    client = FastembedEmbedClient(_KNOWN_MODEL)
    embeddings = client.encode(["x", "y"], normalize_embeddings=False)
    norms = np.linalg.norm(embeddings, axis=1)
    assert not np.allclose(norms, 1.0)


def test_unknown_model_falls_back_to_probe_embedding() -> None:
    client = FastembedEmbedClient("custom/unlisted-model")
    assert client.get_embedding_dimension() == _KNOWN_DIM


def test_module_stays_import_light() -> None:
    # The client imports fastembed lazily, so importing the module must not
    # require the heavy dependency to be present.
    assert "fastembed" not in dir(fe_module)
