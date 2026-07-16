"""Launch / relaunch a pipeline run (``POST /pipeline-runs/{id}/launch``).

Orchestrates the run-status side of launching: it guards the current status,
publishes seed messages via ``seed_pipeline`` (the low-level publisher in
``pipeline/launch.py``), then advances the run to ``"running"``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from dramatiq.brokers.rabbitmq import RabbitmqBroker
from fastapi import HTTPException

from backend.server.pipeline.launch import seed_pipeline
from backend.server.pipeline.schemas import PipelineRunOut, pipeline_run_to_out
from backend.server.pipeline.service.common import parse_run_id
from backend.shared.storage.sql.sql_store import SqlStore


def launch_pipeline_run(
    store: SqlStore, broker: RabbitmqBroker, run_id: str
) -> PipelineRunOut:
    """Launch (or relaunch) a pipeline run by publishing its seed messages.

    Allowed from statuses: ``"pending"``, ``"failed"``, ``"completed"``.
    Returns 409 if the run is already ``"running"``.

    On success the run transitions to ``"running"`` with ``started_at`` set
    to now and ``finished_at`` cleared (so a relaunch starts a clean time
    window even when the previous run had already finished or failed).
    """
    parsed = parse_run_id(run_id)
    run = store.pipeline_runs.get(parsed)
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    if run.status == "running":
        raise HTTPException(
            status_code=409,
            detail="Pipeline run is already running",
        )

    # Publish seed messages on the shared broker — pipeline_id flows into
    # every actor message. ``seed_pipeline`` raises ``ValueError`` if the run's
    # stored dataset snapshot has an unsupported ``source_type``; map it to a
    # 400 rather than letting it fall through as an opaque 500 (see the error
    # handling section in this package's README).
    try:
        seed_pipeline(
            pipeline_id=run.id,
            dataset_snapshot=run.dataset,
            broker=broker,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Advance to "running"; clear finished_at so a relaunch starts clean.
    updated = store.pipeline_runs.update_status(
        run.id,
        "running",
        started_at=datetime.now(tz=timezone.utc),
        reset_finished=True,
    )
    return pipeline_run_to_out(updated or run)
