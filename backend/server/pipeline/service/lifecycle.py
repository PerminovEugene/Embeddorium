"""Read + lifecycle operations for pipeline runs.

The short CRUD-ish operations that don't warrant a module each: listing runs,
fetching one run (with live chunk-progress counts), manual status updates,
deletion (plus on-disk file cleanup), and the paginated crawl-targets view.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from backend.server.pipeline.schemas import (
    PipelineRunOut,
    PipelineRunStatusIn,
    PipelineRunTargetsPage,
    pipeline_run_target_to_out,
    pipeline_run_to_out,
)
from backend.server.pipeline.service.common import TERMINAL_STATUSES, parse_run_id
from backend.shared.pipeline.source_files import delete_run_files
from backend.shared.storage.sql.sql_store import SqlStore


def list_pipeline_runs(store: SqlStore) -> list[PipelineRunOut]:
    """List every pipeline run, newest first."""
    return [pipeline_run_to_out(r) for r in store.pipeline_runs.list_recent()]


def get_pipeline_run(store: SqlStore, run_id: str) -> PipelineRunOut:
    """Fetch a single pipeline run by id, or 404 if it doesn't exist.

    Includes ``chunksEmbedded``/``chunksPending`` — a run-wide "N chunks
    processed / X chunks in progress" summary derived from a live
    ``document_chunks`` aggregate (see
    ``ChunkRepository.status_counts_for_pipeline``), so this is one extra
    query beyond the run row itself.
    """
    parsed = parse_run_id(run_id)
    run = store.pipeline_runs.get(parsed)
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    counts = store.chunks.status_counts_for_pipeline(parsed)
    chunks_embedded = counts.get("embedded", 0)
    chunks_pending = sum(n for status, n in counts.items() if status != "embedded")
    return pipeline_run_to_out(
        run, chunks_embedded=chunks_embedded, chunks_pending=chunks_pending
    )


def update_pipeline_run_status(
    store: SqlStore, run_id: str, payload: PipelineRunStatusIn
) -> PipelineRunOut:
    """Manually update a pipeline run's status.

    When the new status is terminal (``"completed"`` or ``"failed"``),
    ``finished_at`` is also set to now. This is intended for operator
    overrides; the pipeline actors do not call it.
    """
    parsed = parse_run_id(run_id)
    run = store.pipeline_runs.get(parsed)
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    finished_at = (
        datetime.now(tz=timezone.utc) if payload.status in TERMINAL_STATUSES else None
    )
    updated = store.pipeline_runs.update_status(
        parsed,
        payload.status,
        finished_at=finished_at,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return pipeline_run_to_out(updated)


def list_pipeline_run_targets(
    store: SqlStore, run_id: str, limit: int, offset: int
) -> PipelineRunTargetsPage:
    """Paginated list of crawl targets (processed files/URLs) for a run.

    ``limit`` is clamped to 200 (default 50 at the route); ``offset`` is floored
    at 0. Each item includes the source URL, its pipeline status, any skip/error
    detail, and the number of document chunks produced. A chunk count of 0 means
    the target was skipped, failed, or is still in flight.
    """
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    parsed = parse_run_id(run_id)
    run = store.pipeline_runs.get(parsed)
    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    total = store.crawl_targets.count_by_pipeline(parsed)
    pairs = store.crawl_targets.list_by_pipeline(parsed, limit=limit, offset=offset)
    items = [pipeline_run_target_to_out(t, n) for t, n in pairs]
    return PipelineRunTargetsPage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


def delete_pipeline_run(store: SqlStore, run_id: str) -> dict:
    """Delete a pipeline run (and its on-disk files), or 404 if it's unknown."""
    parsed = parse_run_id(run_id)
    deleted = store.pipeline_runs.delete(parsed)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    delete_run_files(str(parsed))
    return {"status": "deleted"}
