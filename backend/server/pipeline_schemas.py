"""camelCase API schemas for the ``/pipeline-runs`` endpoints.

Request/response bodies use camelCase to match the frontend convention; route
handlers translate to/from the snake_case domain models in
``backend.shared.models``. These are pure API-layer types — no business logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from backend.shared.models import PipelineRun


class _CamelModel(BaseModel):
    """Base for API schemas: camelCase on the wire, snake_case in Python."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PipelineRunIn(_CamelModel):
    """Request body for creating a pipeline run.

    ``actor_settings`` carries the form's full per-actor configuration, keyed
    by actor key with camelCase setting keys inside, e.g.::

        {
          "chunk_document": {"strategy": "section", "chunkSize": 1200, ...},
          "embed_chunks": {"providerId": "<uuid>", "similarity": "cosine"},
          "fetch_source": {"verifyTls": true, "timeoutSeconds": 30, ...},
          ...
        }

    The route resolves it into a typed ``PipelineActorConfigs`` snapshot.
    ``embed_chunks.providerId`` is required (validated in the route) because
    every run must have an embedding provider.
    """

    name: Optional[str] = None
    dataset_id: uuid.UUID
    actor_settings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class PipelineRunOut(_CamelModel):
    """Response body for a pipeline run.

    The embedding provider snapshot lives inside ``actor_configs.embed_chunks``
    rather than at the top level; callers should read it from there.
    """

    id: uuid.UUID
    name: Optional[str] = None
    dataset: Dict[str, Any]
    actor_configs: Dict[str, Any]
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class PipelineRunStatusIn(_CamelModel):
    """Request body for ``PATCH /pipeline-runs/{id}`` — update status only.

    Allows an operator (or future tooling) to manually advance a run to any
    valid lifecycle state.  Terminal statuses (``"completed"`` / ``"failed"``)
    cause the handler to set ``finished_at`` automatically.
    """

    status: Literal["pending", "running", "completed", "failed"]


def pipeline_run_to_out(run: PipelineRun) -> PipelineRunOut:
    """Map a domain ``PipelineRun`` to its camelCase response schema."""
    return PipelineRunOut(
        id=run.id,
        name=run.name,
        dataset=run.dataset,
        actor_configs=run.actor_configs,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    )
