"""Async embedding helper for the compare/search API layers.

Reuses ``backend.shared``'s embed clients (the same ones the ingestion pipeline
uses) so the API scores vectors produced exactly like the pipeline's. Provider
selection is *not* handled here: callers resolve the run/provider snapshot into a
concrete :class:`~backend.shared.clients.embed_client.EmbedClient` via the
provider-type adapter registry (:func:`build_embed_client`) and hand it in, so
there is no per-provider branching in this module — the same clean strategy the
embed_chunks actor uses.

The only thing left here is the async plumbing: run the client's blocking
``encode`` off the event loop (Ollama/OpenAI make HTTP calls) so concurrent
requests aren't serialized on it, and normalize to match the ingestion side
(embed_chunks always stores
L2-normalized vectors — without this a "dot" collection returns ‖q‖·cos(q,d)
instead of cos(q,d), an unbounded score that isn't comparable across queries).
"""

from __future__ import annotations

import asyncio

from backend.plugins.provider_types.registry import build_embed_client
from backend.shared.clients.embed_client import EmbedClient


async def embed_texts(client: EmbedClient, texts: list[str]) -> list[list[float]]:
    """Embed *texts* with an already-built client, off the event loop.

    Vectors are L2-normalized to match the ingestion side so "dot" collections
    return true cosine scores.
    """
    embeddings = await asyncio.to_thread(
        client.encode, texts, normalize_embeddings=True
    )
    return embeddings.tolist()


async def get_embeddings(
    provider_type: str,
    model_type: str,
    provider_config: dict | None,
    texts: list[str],
) -> list[list[float]]:
    """Build the client for a ``(provider_type, model_type, config)`` triple and embed.

    The single embedding entry point for compare and search: it dispatches
    through the provider-type adapter registry (the sole owner of how each
    client is built) instead of an inline provider switch.
    """
    client = build_embed_client(provider_type, model_type, provider_config)
    return await embed_texts(client, texts)
