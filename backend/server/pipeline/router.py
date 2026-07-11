"""CRD + launch endpoints for ``PipelineRun`` rows (``/pipeline-runs``).

A pipeline run captures a full snapshot of the dataset and embedding provider
at launch time, so each run is self-contained: actors read config by run id,
and the DB-search UI can list runs with all relevant metadata.

The embedding provider snapshot is stored inside
``actor_configs.embed_chunks.provider`` — it is an embed_chunks concern, not
a top-level run property.

Request/response bodies use camelCase (see ``pipeline/schemas.py``).

These handlers are thin controllers: each parses the request and delegates to
``backend.server.pipeline.service`` (see that package for the business logic,
status-transition rules, and the settings-resolution helpers).

POST  /pipeline-runs                  — create a run (status="pending").
GET   /pipeline-runs                  — list runs, newest first.
GET   /pipeline-runs/{id}             — fetch a single run by id.
POST  /pipeline-runs/{id}/launch      — launch (or relaunch) a run.
PATCH /pipeline-runs/{id}             — update status manually.
DELETE /pipeline-runs/{id}            — delete a run.
"""

from __future__ import annotations

from typing import List

from dramatiq.brokers.rabbitmq import RabbitmqBroker
from fastapi import APIRouter, Depends

from backend.server.dependencies import get_broker, get_sql_store
from backend.server.pipeline import service
from backend.server.pipeline.schemas import (
    PipelineRunIn,
    PipelineRunOut,
    PipelineRunStatusIn,
    PipelineRunTargetsPage,
)
from backend.shared.storage.sql.sql_store import SqlStore

router = APIRouter(prefix="/pipeline-runs", tags=["pipeline-runs"])


@router.get("", response_model=List[PipelineRunOut], response_model_by_alias=True)
async def list_pipeline_runs(
    store: SqlStore = Depends(get_sql_store),
) -> List[PipelineRunOut]:
    """List every pipeline run, newest first."""
    return service.list_pipeline_runs(store)


@router.post("", response_model=PipelineRunOut, response_model_by_alias=True)
async def create_pipeline_run(
    payload: PipelineRunIn, store: SqlStore = Depends(get_sql_store)
) -> PipelineRunOut:
    """Create a pipeline run row with ``status="pending"``; do not launch yet."""
    return service.create_pipeline_run(store, payload)


@router.post(
    "/{run_id}/launch",
    response_model=PipelineRunOut,
    response_model_by_alias=True,
)
async def launch_pipeline_run(
    run_id: str,
    store: SqlStore = Depends(get_sql_store),
    broker: RabbitmqBroker = Depends(get_broker),
) -> PipelineRunOut:
    """Launch (or relaunch) a pipeline run by publishing its seed messages."""
    return service.launch_pipeline_run(store, broker, run_id)


@router.patch(
    "/{run_id}",
    response_model=PipelineRunOut,
    response_model_by_alias=True,
)
async def update_pipeline_run_status(
    run_id: str,
    payload: PipelineRunStatusIn,
    store: SqlStore = Depends(get_sql_store),
) -> PipelineRunOut:
    """Manually update a pipeline run's status."""
    return service.update_pipeline_run_status(store, run_id, payload)


@router.get(
    "/{run_id}/targets",
    response_model=PipelineRunTargetsPage,
    response_model_by_alias=True,
)
async def list_pipeline_run_targets(
    run_id: str,
    limit: int = 50,
    offset: int = 0,
    store: SqlStore = Depends(get_sql_store),
) -> PipelineRunTargetsPage:
    """Paginated list of crawl targets (processed files/URLs) for a run."""
    return service.list_pipeline_run_targets(store, run_id, limit, offset)


@router.get("/{run_id}", response_model=PipelineRunOut, response_model_by_alias=True)
async def get_pipeline_run(
    run_id: str, store: SqlStore = Depends(get_sql_store)
) -> PipelineRunOut:
    """Fetch a single pipeline run by id, or 404 if it doesn't exist."""
    return service.get_pipeline_run(store, run_id)


@router.delete("/{run_id}")
async def delete_pipeline_run(
    run_id: str, store: SqlStore = Depends(get_sql_store)
) -> dict:
    """Delete a pipeline run, or 404 if it doesn't exist."""
    return service.delete_pipeline_run(store, run_id)
