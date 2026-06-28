"""Single source of truth for Qdrant collection naming + similarity.

The ingestion pipeline stores one collection per ``group``, named
``LAWS_<group>_qwen_embed_8b``. Keeping the parts here (instead of inline in the
embed launcher) lets the pipeline-run recorder reproduce the exact collection
name and similarity a run will use, without importing the launcher (which builds
a RabbitMQ broker at import time).
"""

COLLECTION_BASE = "LAWS"
MODEL_COLLECTION_POSTFIX = "qwen_embed_8b"

# Distance metric collections are created with — mirrors ``Distance.COSINE`` in
# ``VectorStore.create_collection``. Stored as the persisted similarity name.
COLLECTION_SIMILARITY = "cosine"


def build_collection_name(group: str) -> str:
    """Return the Qdrant collection name the pipeline uses for *group*."""
    return f"{COLLECTION_BASE}_{group}_{MODEL_COLLECTION_POSTFIX}"
