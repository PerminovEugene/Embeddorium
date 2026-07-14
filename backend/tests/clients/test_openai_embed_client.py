"""OpenAI-compatible embedding HTTP client behavior."""

from __future__ import annotations

import httpx
import numpy as np

import backend.shared.clients.openai_embed_client as client_module
from backend.shared.clients.openai_embed_client import OpenAIEmbedClient


def test_encode_posts_batches_in_index_order_and_normalizes(monkeypatch) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.0, 2.0]},
                    {"index": 0, "embedding": [3.0, 0.0]},
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        client_module.httpx,
        "Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )
    client = OpenAIEmbedClient(
        model="embed-v1",
        base_url="https://example.test/v1",
        api_key="secret",
    )

    vectors = client.encode(["a", "b"], batch_size=2, normalize_embeddings=True)

    np.testing.assert_allclose(vectors, [[1.0, 0.0], [0.0, 1.0]])
    assert requests[0].url == "https://example.test/v1/embeddings"
    assert requests[0].headers["authorization"] == "Bearer secret"
