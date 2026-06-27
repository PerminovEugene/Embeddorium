"""Embedding access for the matcher API.

Reuses ``laws_agent``'s ``OllamaEmbedClient`` (the same client the ingestion
pipeline uses for ``EMBED_PROVIDER=ollama``) instead of talking to Ollama with
raw HTTP, so the tester scores vectors produced exactly like the pipeline's.

The UI lets the user pick the Ollama port (and model) per request, so a client
is built per call from that port; ``OLLAMA_HOST`` (default
``host.docker.internal``, so a container can reach an Ollama on the host) sets
the host half of the URL.
"""

import asyncio
import os
from typing import List

from laws_agent.clients.ollama_embed_client import OllamaEmbedClient

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "host.docker.internal")


async def get_embeddings(
    model: str, ollama_port: str, texts: List[str]
) -> List[List[float]]:
    base_url = f"http://{OLLAMA_HOST}:{ollama_port}"
    client = OllamaEmbedClient(model=model, base_url=base_url)

    # OllamaEmbedClient.encode is a blocking HTTP call; run it off the event
    # loop so concurrent requests aren't serialized on it.
    embeddings = await asyncio.to_thread(client.encode, texts)
    return embeddings.tolist()
