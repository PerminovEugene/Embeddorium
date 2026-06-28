"""Embedding access for the matcher API.

Reuses ``laws_agent``'s embed clients (the same ones the ingestion pipeline
uses) instead of talking to a provider with raw HTTP, so the tester scores
vectors produced exactly like the pipeline's. The provider is selected per
request from the pipeline run's recorded embed config, mirroring
``embed_chunks_actor.handler.get_model_and_size``:

- ``ollama``: call a remote Ollama server (``OLLAMA_HOST``, default
  ``host.docker.internal`` so a container can reach an Ollama on the host, plus
  the per-request port).
- ``mock``: generate random vectors of the run's ``mock_dim`` — no network,
  for fast local/testing runs against a collection built the same way.

The UI lets the user pick the Ollama port (and model) per request, so an Ollama
client is built per call from that port.
"""

import asyncio
import os
from typing import List, Optional

from laws_agent.clients.mock_embed_client import MockEmbedClient
from laws_agent.clients.ollama_embed_client import OllamaEmbedClient

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "host.docker.internal")


async def get_embeddings(
    provider: str,
    model: str,
    ollama_port: Optional[str],
    texts: List[str],
    *,
    mock_dim: Optional[int] = None,
) -> List[List[float]]:
    if provider == "mock":
        # No network: random vectors of the run's indexed dimension. The
        # dimension must match the collection, so it comes from the run's
        # recorded config, not a default here.
        if mock_dim is None:
            raise ValueError("mock provider requires mock_dim from the run config")
        client = MockEmbedClient(dimension=mock_dim)
        embeddings = await asyncio.to_thread(client.encode, texts)
        return embeddings.tolist()

    base_url = f"http://{OLLAMA_HOST}:{ollama_port}"
    client = OllamaEmbedClient(model=model, base_url=base_url)

    # OllamaEmbedClient.encode is a blocking HTTP call; run it off the event
    # loop so concurrent requests aren't serialized on it.
    embeddings = await asyncio.to_thread(client.encode, texts)
    return embeddings.tolist()
