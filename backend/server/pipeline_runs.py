"""Pipeline-run utilities for the matcher API.

The DB-search source mode lists ingestion *pipeline runs* recorded in Postgres
(``pipeline_runs``), each of which already captures the collection it populated
and the embedding provider/model it was built with. Selecting a run therefore
reuses exactly that run's launch configuration, so a query is embedded with the
same model the collection was indexed with (no more dimension/model mismatches).
"""

from __future__ import annotations

import uuid
from typing import Optional

from backend.shared.models import PipelineRun
from backend.shared.storage.sql.sql_store import SqlStore


def _serialize(run: PipelineRun) -> dict:
    """Flatten a run into the shape the UI's run selector consumes."""
    actor_cfg = run.actor_configs
    vector_store_cfg = actor_cfg.get("vector_store", {})
    chunk_cfg = actor_cfg.get("chunk_document", {})
    # Provider snapshot lives in actor_configs.embed_chunks.provider.
    provider = actor_cfg.get("embed_chunks", {}).get("provider", {})
    dataset = run.dataset

    return {
        "id": str(run.id),
        "name": run.name or "",
        "datasetName": dataset.get("name", ""),
        "datasetSourceType": dataset.get("source_type", ""),
        "collection": vector_store_cfg.get("collection", ""),
        "embedProvider": provider.get("provider_type", ""),
        "embedModel": provider.get("model_name") or provider.get("model", ""),
        "similarity": vector_store_cfg.get("similarity", ""),
        "chunkSize": chunk_cfg.get("chunk_size"),
        "chunkOverlap": chunk_cfg.get("chunk_overlap"),
        "status": run.status,
        "createdAt": run.created_at.isoformat() if run.created_at else None,
    }


def list_pipeline_runs() -> list:
    """Return every recorded pipeline run, newest first, for the run selector."""
    store = SqlStore(application_name="embeddorium-runs")
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

    store = SqlStore(application_name="embeddorium-runs")
    try:
        return store.pipeline_runs.get(parsed)
    finally:
        store.close()
