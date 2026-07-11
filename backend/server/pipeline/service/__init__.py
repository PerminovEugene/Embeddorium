"""Service layer for the ``/pipeline-runs`` endpoints.

Thin facade that composes the focused operation modules so the router can stay
a set of one-line controllers:

* ``create`` — validate + snapshot + persist a new run (the substantial one).
* ``launch`` — status-guarded launch/relaunch that publishes the seed messages.
* ``lifecycle`` — list, fetch, status update, delete, and crawl-targets paging.

Each operation raises the same typed ``HTTPException``\\ s the handlers used to
raise inline, so behaviour (status codes, detail strings) is unchanged.
"""

from __future__ import annotations

from backend.server.pipeline.service.create import create_pipeline_run
from backend.server.pipeline.service.launch import launch_pipeline_run
from backend.server.pipeline.service.lifecycle import (
    delete_pipeline_run,
    get_pipeline_run,
    list_pipeline_run_targets,
    list_pipeline_runs,
    update_pipeline_run_status,
)

__all__ = [
    "create_pipeline_run",
    "delete_pipeline_run",
    "get_pipeline_run",
    "launch_pipeline_run",
    "list_pipeline_run_targets",
    "list_pipeline_runs",
    "update_pipeline_run_status",
]
