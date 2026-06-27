"""Qdrant persistence for the matcher API.

Reuses ``laws_agent``'s ``VectorStore`` (which reads ``config.QDRANT_URL``)
instead of a private Qdrant client, so the tester writes to the same instance
as the pipeline and inherits its (idempotent, non-destructive) collection
handling. Each model gets its own collection, keyed by model + dimension, so
vectors of different widths never collide.
"""

from laws_agent.storage.vector.vector_store import VectorStore


def get_store(model_name: str, dim_size: int) -> VectorStore:
    """Return a VectorStore for *model_name*, creating the collection if absent."""
    collection = f"embedorium_{model_name}_{dim_size}"
    store = VectorStore(collection=collection)
    store.create_collection(dim_size)
    return store


def store_vectors(store, texts, embeddings, request_uuid, group_name):
    """Upsert *texts*/*embeddings* into *store*, tagged by request and group."""
    payloads = [
        {
            "request_uuid": request_uuid,
            "text": item.text,
            "group_id": item.id,
            "group": group_name,
        }
        for item in texts
    ]
    store.upsert(vectors=embeddings, payloads=payloads)
