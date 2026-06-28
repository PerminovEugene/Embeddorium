"""Pipeline-run listing for the matcher API.

The DB-search source mode no longer asks the user to hand-pick a raw Qdrant
collection plus an embedding model. Instead it lists the ingestion *pipeline
runs* recorded in Postgres (``pipeline_runs``), each of which already captures
the collection it populated and the embedding provider/model it was built with.
Selecting a run therefore reuses exactly that run's launch configuration, so a
query is embedded with the same model the collection was indexed with (no more
dimension/model mismatches).
"""

from __future__ import annotations

import uuid
from typing import Optional

from laws_agent.models import PipelineRun
from laws_agent.storage.sql.sql_store import SqlStore


def _serialize(run: PipelineRun) -> dict:
    """Flatten a run into the shape the UI's run selector consumes."""
    embed = run.settings.embed_chunks
    vector = run.settings.vector_store
    chunk = run.settings.chunk_document
    return {
        "id": str(run.id),
        "group": run.group,
        "sourceType": run.source_type,
        "collection": run.collection_name,
        "embedProvider": embed.provider,
        "embedModel": embed.model,
        "similarity": vector.similarity,
        "chunkSize": chunk.chunk_size,
        "chunkOverlap": chunk.chunk_overlap,
        "createdAt": run.created_at.isoformat() if run.created_at else None,
    }


def list_pipeline_runs() -> list[dict]:
    """Return every recorded pipeline run, newest first, for the run selector."""
    store = SqlStore(application_name="embedorium-runs")
    try:
        return [_serialize(run) for run in store.pipeline_runs.list_recent()]
    finally:
        store.close()


def get_pipeline_run(run_id: str) -> Optional[PipelineRun]:
    """Load a single run by id, or ``None`` if the id is unknown/malformed."""
    try:
        parsed = uuid.UUID(str(run_id))
    except (ValueError, TypeError):
        return None

    store = SqlStore(application_name="embedorium-runs")
    try:
        return store.pipeline_runs.get(parsed)
    finally:
        store.close()
