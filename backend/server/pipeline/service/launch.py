"""Launch / relaunch a pipeline run (``POST /pipeline-runs/{id}/launch``).

Orchestrates the run-status side of launching: it guards the current status,
resolves the seed-time file glob from the run's stored config, publishes the
seed messages via ``seed_pipeline`` (the low-level publisher in
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

    # The local-file glob is a seed-time concern (it decides which files a
    # folder path expands to), so resolve it here from the stored config.
    # Read the raw dict rather than the typed model so runs recorded
    # before the fetch actors were merged (fetch_file_source.glob) still
    # relaunch with their original glob.
    raw_cfgs = run.actor_configs or {}
    file_glob = (
        (raw_cfgs.get("fetch_source") or {}).get("file_glob")
        or (raw_cfgs.get("fetch_file_source") or {}).get("glob")
        or "*.xml"
    )

    # Publish seed messages on the shared broker — pipeline_id flows into
    # every actor message.
    seed_pipeline(
        pipeline_id=run.id,
        dataset_snapshot=run.dataset,
        file_glob=file_glob,
        broker=broker,
    )

    # Advance to "running"; clear finished_at so a relaunch starts clean.
    updated = store.pipeline_runs.update_status(
        run.id,
        "running",
        started_at=datetime.now(tz=timezone.utc),
        reset_finished=True,
    )
    return pipeline_run_to_out(updated or run)
