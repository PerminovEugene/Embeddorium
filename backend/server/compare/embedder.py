"""Embedding access for the matcher API.

Reuses ``backend.shared``'s embed clients (the same ones the ingestion pipeline
uses) instead of talking to a provider with raw HTTP, so the tester scores
vectors produced exactly like the pipeline's. The provider is selected per
request from the pipeline run's recorded embed config, mirroring
``embed_chunks_actor.handler.get_model_and_size``:

- ``ollama``: call a remote Ollama server at a caller-supplied ``base_url``.
  ``OLLAMA_HOST`` (default ``host.docker.internal`` so a container can reach an
  Ollama on the host) is exported for callers that still assemble a URL from a
  saved provider's port (compare); search passes the pipeline's own
  ``OLLAMA_EMBED_BASE_URL`` so the query is embedded via the same endpoint the
  collection was indexed with.
- ``mock``: generate random vectors of the run's ``mock_dim`` — no network,
  for fast local/testing runs against a collection built the same way.
- ``fastembed``: run a local ONNX model in-process via FastEmbed — no network,
  ignores ``base_url``.
"""

import asyncio
import os
from typing import List, Optional

from backend.shared.clients.mock_embed_client import MockEmbedClient
from backend.shared.clients.ollama_embed_client import OllamaEmbedClient

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "host.docker.internal")


async def get_embeddings(
    provider: str,
    model: str,
    base_url: Optional[str],
    texts: List[str],
    *,
    mock_dim: Optional[int] = None,
    api_key: str | None = None,
) -> List[List[float]]:
    """Embed ``texts`` with the selected provider.

    For the ``ollama`` provider the client talks to ``base_url`` directly — the
    caller resolves the endpoint (a saved provider's host/port for compare, or
    the pipeline's ``OLLAMA_EMBED_BASE_URL`` for search) so it is never taken
    from the browser. ``mock`` needs no endpoint and returns random vectors of
    ``mock_dim``.
    """
    if provider == "mock":
        # No network: random vectors of the run's indexed dimension. The
        # dimension must match the collection, so it comes from the run's
        # recorded config, not a default here.
        if mock_dim is None:
            raise ValueError("mock provider requires mock_dim from the run config")
        client = MockEmbedClient(dimension=mock_dim)
        # Normalize to match the ingestion side (embed_chunks_actor always
        # stores L2-normalized vectors). Without this, a "dot" collection
        # returns ‖q‖·cos(q,d) instead of cos(q,d) — an unbounded score that
        # isn't comparable across queries.
        embeddings = await asyncio.to_thread(
            client.encode, texts, normalize_embeddings=True
        )
        return embeddings.tolist()

    if provider == "fastembed":
        # Fully local ONNX model — no network, ``base_url`` is ignored. Deferred
        # import so the fastembed/onnxruntime stack is only pulled on this path.
        from backend.shared.clients.fastembed_embed_client import (
            FastembedEmbedClient,
        )

        client = FastembedEmbedClient(model)
        # Run the blocking encode off the event loop. Normalize to match the
        # ingestion side so "dot" collections return true cosine scores.
        embeddings = await asyncio.to_thread(
            client.encode, texts, normalize_embeddings=True
        )
        return embeddings.tolist()

    if provider == "openai":
        from backend.shared.clients.openai_embed_client import OpenAIEmbedClient

        if not base_url:
            raise ValueError("openai provider requires a base_url")
        client = OpenAIEmbedClient(
            model=model,
            base_url=base_url,
            api_key=api_key,
        )
        embeddings = await asyncio.to_thread(
            client.encode,
            texts,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    client = OllamaEmbedClient(model=model, base_url=base_url)

    # OllamaEmbedClient.encode is a blocking HTTP call; run it off the event
    # loop so concurrent requests aren't serialized on it. Normalize to match
    # the ingestion side so "dot" collections return true cosine scores.
    embeddings = await asyncio.to_thread(
        client.encode, texts, normalize_embeddings=True
    )
    return embeddings.tolist()
