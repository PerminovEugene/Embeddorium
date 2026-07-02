"""camelCase API schemas for the ``/pipeline-runs`` endpoints.

Request/response bodies use camelCase to match the frontend convention; route
handlers translate to/from the snake_case domain models in
``backend.shared.models``. These are pure API-layer types — no business logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from backend.shared.models import PipelineRun
from backend.shared.models.crawl_target import CrawlTarget


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


class PipelineRunTargetOut(_CamelModel):
    """One crawl target row in a pipeline run's processed-files response.

    ``url`` is mapped from ``original_url`` on the domain model; the alias
    generator produces camelCase wire names for all multi-word fields
    (e.g. ``normalizedUrl``, ``skipReason``, ``chunkCount``).
    """

    id: uuid.UUID
    # original_url is exposed as the shorter "url" key to keep the wire schema
    # clean; normalizedUrl carries the full canonical form.
    url: str
    normalized_url: str
    status: str
    skip_reason: Optional[str] = None
    error: Optional[str] = None
    chunk_count: int
    document_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PipelineRunTargetsPage(_CamelModel):
    """Paginated list of crawl targets for a single pipeline run."""

    items: List[PipelineRunTargetOut]
    total: int
    limit: int
    offset: int


def pipeline_run_target_to_out(
    target: CrawlTarget, chunk_count: int
) -> PipelineRunTargetOut:
    """Map a domain ``CrawlTarget`` + its chunk count to the response schema."""
    return PipelineRunTargetOut(
        id=target.id,
        url=target.original_url,
        normalized_url=target.normalized_url,
        status=str(target.status),
        skip_reason=target.skip_reason,
        error=target.error,
        chunk_count=chunk_count,
        document_id=target.document_id,
        created_at=target.created_at,
        updated_at=target.updated_at,
    )


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
