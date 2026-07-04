"""Single source of truth for Qdrant collection naming + similarity.

The ingestion pipeline stores one collection per dataset, named
``BASE_<dataset_name>_qwen_embed_8b``. Keeping the parts here (instead of inline
in the embed launcher) lets the pipeline-run recorder reproduce the exact
collection name and similarity a run will use, without importing the launcher
(which builds a RabbitMQ broker at import time).
"""

COLLECTION_BASE = "BASE"
MODEL_COLLECTION_POSTFIX = "qwen_embed_8b"

# Distance metric collections are created with — mirrors ``Distance.COSINE`` in
# ``VectorStore.create_collection``. Stored as the persisted similarity name.
COLLECTION_SIMILARITY = "cosine"

# Used only when no pipeline_id is available to look up a run's recorded
# collection (legacy messages predating pipeline_id tracking). Every current
# entry point records a pipeline_id, so this path should not be hit in
# practice.
UNSCOPED_DATASET_NAME = "unscoped"


def build_collection_name(dataset_name: str) -> str:
    """Return the Qdrant collection name the pipeline uses for *dataset_name*."""
    return f"{COLLECTION_BASE}_{dataset_name}_{MODEL_COLLECTION_POSTFIX}"
