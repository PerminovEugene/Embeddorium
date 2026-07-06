"""CRD + launch endpoints for ``PipelineRun`` rows (``/pipeline-runs``).

A pipeline run captures a full snapshot of the dataset and embedding provider
at launch time, so each run is self-contained: actors read config by run id,
and the DB-search UI can list runs with all relevant metadata.

The embedding provider snapshot is stored inside
``actor_configs.embed_chunks.provider`` — it is an embed_chunks concern, not
a top-level run property.

Request/response bodies use camelCase (see ``pipeline/schemas.py``).

POST  /pipeline-runs                  — create a run (status="pending").
GET   /pipeline-runs                  — list runs, newest first.
GET   /pipeline-runs/{id}             — fetch a single run by id.
POST  /pipeline-runs/{id}/launch      — launch (or relaunch) a run.
PATCH /pipeline-runs/{id}             — update status manually.
DELETE /pipeline-runs/{id}            — delete a run.

Status-transition rules
-----------------------
* ``POST /pipeline-runs``          → always ``"pending"`` on creation.
* ``POST /pipeline-runs/{id}/launch``
  - Allowed from: ``"pending"``, ``"failed"``, ``"completed"`` (relaunch).
  - Guard: 409 when status is already ``"running"``.
  - Transitions to ``"running"``; sets ``started_at=now()`` and clears
    ``finished_at`` (so a relaunched run starts with a clean time window).
* ``PATCH /pipeline-runs/{id}``    → any valid status set by the caller;
  terminal statuses (``"completed"``/``"failed"``) also set ``finished_at``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Type, TypeVar

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pydantic.alias_generators import to_snake

from backend.plugins.chunkers.registry import DEFAULT_CHUNKER
from backend.server.pipeline.launch import seed_pipeline
from backend.server.pipeline.schemas import (
    PipelineRunIn,
    PipelineRunOut,
    PipelineRunStatusIn,
    PipelineRunTargetsPage,
    pipeline_run_target_to_out,
    pipeline_run_to_out,
)
from backend.shared.models import PipelineActorConfigs, PipelineRun
from backend.shared.models.pipeline_run import (
    ChunkDocumentSettings,
    CrawlFrontierManagerSettings,
    EmbedChunksSettings,
    FetchFileSourceSettings,
    FetchSourceSettings,
    FilterDocumentsSettings,
    ParseSourceSettings,
    ScheduleDiscoveredLinksSettings,
    ScheduleEmbeddingsSettings,
    VectorStoreSettings,
)
from backend.shared.pipeline.source_files import delete_run_files
from backend.shared.storage.sql.sql_store import SqlStore
from backend.shared.storage.vector.collection_naming import (
    COLLECTION_SIMILARITY,
    build_collection_name,
)

router = APIRouter(prefix="/pipeline-runs", tags=["pipeline-runs"])

_TERMINAL_STATUSES = {"completed", "failed"}

# VectorStoreSettings.similarity is a tight enum; the UI picker offers more
# options, so anything outside this set falls back to the global default.
_VALID_SIMILARITY = {"cosine", "dot", "euclid"}

_SettingsT = TypeVar("_SettingsT", bound=BaseModel)


def _parse_id(run_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(run_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Pipeline run not found")


def _parse_provider_id(raw: Any) -> uuid.UUID:
    """Parse the required embed_chunks providerId, or 400 if missing/invalid."""
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="actorSettings.embed_chunks.providerId is required.",
        )
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid providerId: {raw!r}",
        )


def _build_settings(
    model_cls: Type[_SettingsT], block: Dict[str, Any]
) -> _SettingsT:
    """Validate one actor's camelCase UI settings into its snake_case model.

    The form sends camelCase keys (``timeoutSeconds``); the domain models are
    snake_case (``timeout_seconds``), so keys are converted before validation.
    Missing/unknown keys fall back to the model's field defaults, so a partial
    or empty block still yields a fully-resolved settings object.
    """
    snaked = {to_snake(k): v for k, v in (block or {}).items()}
    try:
        return model_cls.model_validate(snaked)
    except Exception:
        # A malformed value (e.g. wrong type) shouldn't 500 the create; fall
        # back to defaults so the run is still created with sane config.
        return model_cls()


@router.get("", response_model=List[PipelineRunOut], response_model_by_alias=True)
async def list_pipeline_runs() -> List[PipelineRunOut]:
    """List every pipeline run, newest first."""
    store = SqlStore(application_name="embeddorium-pipeline-runs")
    try:
        return [pipeline_run_to_out(r) for r in store.pipeline_runs.list_recent()]
    finally:
        store.close()


@router.post("", response_model=PipelineRunOut, response_model_by_alias=True)
async def create_pipeline_run(payload: PipelineRunIn) -> PipelineRunOut:
    """Create a pipeline run row with ``status="pending"``; do not launch yet.

    Steps
    -----
    1. Load the Dataset from the DB (404 if missing).
    2. Read ``provider_id`` from ``payload.actor_configs.provider_id``; load
       the Provider from the DB (404 if missing). Raise 400 if
       ``model_type != "embedding"`` — the embed actor requires an embedding
       provider.
    3. Build ``actor_configs`` from the request overrides + global defaults,
       nesting the provider snapshot under ``actor_configs.embed_chunks``.
    4. Snapshot dataset and provider via ``model_dump(mode="json")``; the
       provider snapshot lives in ``actor_configs.embed_chunks.provider``.
    5. Persist the ``PipelineRun`` row with ``status="pending"``.
    6. Return the created run immediately.

    To publish seed messages and advance the run to ``"running"``, call
    ``POST /pipeline-runs/{id}/launch`` on the returned id.
    """
    store = SqlStore(application_name="embeddorium-pipeline-runs")
    try:
        dataset = store.datasets.get(payload.dataset_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="Dataset not found")

        settings = payload.actor_settings or {}
        embed_block = settings.get("embed_chunks") or {}
        chunk_block = settings.get("chunk_document") or {}

        # provider_id lives inside embed_chunks (it is an embed_chunks concern).
        provider_id = _parse_provider_id(embed_block.get("providerId"))
        provider = store.providers.get(provider_id)
        if provider is None:
            raise HTTPException(status_code=404, detail="Provider not found")

        if provider.model_type != "embedding":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Provider '{provider.name}' has model_type "
                    f"'{provider.model_type}', but an 'embedding' provider "
                    "is required for the embed_chunks actor."
                ),
            )

        # Resolve the three actor blocks the pipeline already consumes from the
        # request overrides + global defaults.
        collection = build_collection_name(dataset.name)
        # chunk_block now arrives as {"chunker": <name>, "settings": {...}};
        # "settings" is the chunker's own declared field values and is stored
        # verbatim — its keys are chunker-declared snake_case, not form
        # camelCase, so (unlike every other block here) they must NOT be
        # run through to_snake.
        similarity = embed_block.get("similarity")
        chunk_cfg = ChunkDocumentSettings(
            chunker=chunk_block.get("chunker") or DEFAULT_CHUNKER,
            settings=chunk_block.get("settings") or {},
        )
        vector_cfg = VectorStoreSettings(
            collection=collection,
            similarity=(
                similarity if similarity in _VALID_SIMILARITY else COLLECTION_SIMILARITY
            ),
        )

        # Provider snapshot lives inside embed_chunks, not at the top level.
        provider_snap = provider.model_dump(mode="json")
        embed_cfg = EmbedChunksSettings(provider=provider_snap)

        # Remaining per-actor blocks pass through verbatim (defaults fill gaps),
        # so every form setting is persisted and available to its actor.
        actor_configs = PipelineActorConfigs(
            chunk_document=chunk_cfg,
            vector_store=vector_cfg,
            embed_chunks=embed_cfg,
            parse_source=_build_settings(
                ParseSourceSettings, settings.get("parse_source", {})
            ),
            schedule_embeddings=_build_settings(
                ScheduleEmbeddingsSettings, settings.get("schedule_embeddings", {})
            ),
            crawl_frontier_manager=_build_settings(
                CrawlFrontierManagerSettings,
                settings.get("crawl_frontier_manager", {}),
            ),
            fetch_source=_build_settings(
                FetchSourceSettings, settings.get("fetch_source", {})
            ),
            schedule_discovered_links=_build_settings(
                ScheduleDiscoveredLinksSettings,
                settings.get("schedule_discovered_links", {}),
            ),
            fetch_file_source=_build_settings(
                FetchFileSourceSettings, settings.get("fetch_file_source", {})
            ),
            filter_documents=_build_settings(
                FilterDocumentsSettings, settings.get("filter_documents", {})
            ),
        )

        # Snapshot the dataset so actors never re-query it.
        dataset_snap = dataset.model_dump(mode="json")

        # Use the user-supplied name, falling back to the dataset name so a run
        # always has a sensible label even if the client omits one.
        name = (payload.name or "").strip() or dataset.name

        run = PipelineRun(
            name=name,
            dataset=dataset_snap,
            actor_configs=actor_configs.model_dump(),
            status="pending",
        )
        created = store.pipeline_runs.create(run)
        return pipeline_run_to_out(created)
    finally:
        store.close()


@router.post(
    "/{run_id}/launch",
    response_model=PipelineRunOut,
    response_model_by_alias=True,
)
async def launch_pipeline_run(run_id: str) -> PipelineRunOut:
    """Launch (or relaunch) a pipeline run by publishing its seed messages.

    Allowed from statuses: ``"pending"``, ``"failed"``, ``"completed"``.
    Returns 409 if the run is already ``"running"``.

    On success the run transitions to ``"running"`` with ``started_at`` set
    to now and ``finished_at`` cleared (so a relaunch starts a clean time
    window even when the previous run had already finished or failed).
    """
    parsed = _parse_id(run_id)
    store = SqlStore(application_name="embeddorium-pipeline-runs")
    try:
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
        try:
            file_glob = (
                PipelineActorConfigs.model_validate(run.actor_configs)
                .fetch_file_source.glob
                or "*.xml"
            )
        except Exception:
            file_glob = "*.xml"

        # Publish seed messages — pipeline_id flows into every actor message.
        seed_pipeline(
            pipeline_id=run.id,
            dataset_snapshot=run.dataset,
            file_glob=file_glob,
        )

        # Advance to "running"; clear finished_at so a relaunch starts clean.
        updated = store.pipeline_runs.update_status(
            run.id,
            "running",
            started_at=datetime.now(tz=timezone.utc),
            reset_finished=True,
        )
        return pipeline_run_to_out(updated or run)
    finally:
        store.close()


@router.patch(
    "/{run_id}",
    response_model=PipelineRunOut,
    response_model_by_alias=True,
)
async def update_pipeline_run_status(
    run_id: str,
    payload: PipelineRunStatusIn,
) -> PipelineRunOut:
    """Manually update a pipeline run's status.

    When the new status is terminal (``"completed"`` or ``"failed"``),
    ``finished_at`` is also set to now.  This endpoint is intended for
    operator overrides; the pipeline actors do not call it.
    """
    parsed = _parse_id(run_id)
    store = SqlStore(application_name="embeddorium-pipeline-runs")
    try:
        run = store.pipeline_runs.get(parsed)
        if run is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")

        finished_at = (
            datetime.now(tz=timezone.utc)
            if payload.status in _TERMINAL_STATUSES
            else None
        )
        updated = store.pipeline_runs.update_status(
            parsed,
            payload.status,
            finished_at=finished_at,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        return pipeline_run_to_out(updated)
    finally:
        store.close()


@router.get(
    "/{run_id}/targets",
    response_model=PipelineRunTargetsPage,
    response_model_by_alias=True,
)
async def list_pipeline_run_targets(
    run_id: str,
    limit: int = 50,
    offset: int = 0,
) -> PipelineRunTargetsPage:
    """Paginated list of crawl targets (processed files/URLs) for a run.

    Query params
    ------------
    limit:  Page size (clamped to 200; default 50).
    offset: Row offset for the current page (floored at 0; default 0).

    Each item includes the source URL, its pipeline status, any skip/error
    detail, and the number of document chunks produced. A chunk count of 0
    means the target was skipped, failed, or is still in flight.
    ``processedAt`` (once set) plus the item's own ``createdAt`` gives that
    target's single-file/URL processing time.
    """
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    parsed = _parse_id(run_id)
    store = SqlStore(application_name="embeddorium-pipeline-runs")
    try:
        run = store.pipeline_runs.get(parsed)
        if run is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")

        total = store.crawl_targets.count_by_pipeline(parsed)
        pairs = store.crawl_targets.list_by_pipeline(
            parsed, limit=limit, offset=offset
        )
        items = [pipeline_run_target_to_out(t, n) for t, n in pairs]
        return PipelineRunTargetsPage(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )
    finally:
        store.close()


@router.get("/{run_id}", response_model=PipelineRunOut, response_model_by_alias=True)
async def get_pipeline_run(run_id: str) -> PipelineRunOut:
    """Fetch a single pipeline run by id, or 404 if it doesn't exist.

    Includes ``chunksEmbedded``/``chunksPending`` — a run-wide "N chunks
    processed / X chunks in progress" summary derived from a live
    ``document_chunks`` aggregate (see
    ``ChunkRepository.status_counts_for_pipeline``), so this is one extra
    query beyond the run row itself.
    """
    parsed = _parse_id(run_id)
    store = SqlStore(application_name="embeddorium-pipeline-runs")
    try:
        run = store.pipeline_runs.get(parsed)
        if run is None:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        counts = store.chunks.status_counts_for_pipeline(parsed)
        chunks_embedded = counts.get("embedded", 0)
        chunks_pending = sum(n for status, n in counts.items() if status != "embedded")
        return pipeline_run_to_out(
            run, chunks_embedded=chunks_embedded, chunks_pending=chunks_pending
        )
    finally:
        store.close()


@router.delete("/{run_id}")
async def delete_pipeline_run(run_id: str) -> dict:
    """Delete a pipeline run, or 404 if it doesn't exist."""
    parsed = _parse_id(run_id)
    store = SqlStore(application_name="embeddorium-pipeline-runs")
    try:
        deleted = store.pipeline_runs.delete(parsed)
        if not deleted:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        delete_run_files(str(parsed))
        return {"status": "deleted"}
    finally:
        store.close()
