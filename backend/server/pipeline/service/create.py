"""Create a ``PipelineRun`` row (``POST /pipeline-runs``).

The one substantial pipeline operation: it validates the request's dataset and
embedding provider, resolves the form's per-actor camelCase settings into a
typed ``PipelineActorConfigs`` snapshot, and persists the run as
``status="pending"`` (launch is a separate step). The settings-resolution
helpers here (``_parse_provider_id``, ``_build_settings``,
``_validate_source_block``) are unique to creation and so live alongside it.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic.alias_generators import to_snake

from backend.plugins.chunkers.registry import DEFAULT_CHUNKER
from backend.server.pipeline.schemas import (
    PipelineRunIn,
    PipelineRunOut,
    pipeline_run_to_out,
)
from backend.shared.models import PipelineActorConfigs, PipelineRun
from backend.shared.models.pipeline_run import (
    ChunkDocumentSettings,
    EmbedChunksSettings,
    FetchSourceSettings,
    FilterDocumentsSettings,
    ParseSourceSettings,
    ScheduleDiscoveredLinksSettings,
    ScheduleEmbeddingsSettings,
    ValidateSourceSettings,
    VectorStoreSettings,
)
from backend.shared.storage.sql.sql_store import SqlStore
from backend.shared.storage.vector.collection_naming import (
    COLLECTION_SIMILARITY,
    build_collection_name,
)

# VectorStoreSettings.similarity is a tight enum; the UI picker offers more
# options, so anything outside this set falls back to the global default.
_VALID_SIMILARITY = {"cosine", "dot", "euclid"}

_SettingsT = TypeVar("_SettingsT", bound=BaseModel)


def _parse_provider_id(raw: Any) -> uuid.UUID:
    """Parse the required embed_chunks provider id, or 400 if missing/invalid."""
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="actorSettings.embed_chunks.provider is required.",
        )
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid providerId: {raw!r}",
        )


def _build_settings(model_cls: type[_SettingsT], block: dict[str, Any]) -> _SettingsT:
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
        # back to defaults so the run is still created with sane config. Log the
        # discarded input, though — silently diverging from what the user asked
        # for is a data-integrity trap for a config-reproducing workbench.
        logging.warning(
            "Discarding malformed %s settings; falling back to defaults. input=%r",
            model_cls.__name__,
            snaked,
            exc_info=True,
        )
        return model_cls()


def _validate_source_block(settings: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Resolve the ``validate_source`` form block, accepting legacy keys.

    Older UI builds send the pre-merge ``crawl_frontier_manager`` block (and a
    ``fetch_file_source.dedup`` toggle for local runs); map those onto the
    merged actor's settings so existing forms keep working.
    """
    block = (
        settings.get("validate_source") or settings.get("crawl_frontier_manager") or {}
    )
    legacy_file = settings.get("fetch_file_source") or {}
    if "dedup" not in block and "dedup" in legacy_file:
        block = {**block, "dedup": legacy_file["dedup"]}
    return block


def create_pipeline_run(store: SqlStore, payload: PipelineRunIn) -> PipelineRunOut:
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
    dataset = store.datasets.get(payload.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    settings = payload.actor_settings or {}
    embed_block = settings.get("embed_chunks") or {}
    chunk_block = settings.get("chunk_document") or {}

    # The provider id lives inside embed_chunks (it is an embed_chunks concern).
    # "provider" is the plugin-declared field key; "providerId" is the legacy
    # key older UI builds send.
    provider_id = _parse_provider_id(
        embed_block.get("provider") or embed_block.get("providerId")
    )
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
        validate_source=_build_settings(
            ValidateSourceSettings, _validate_source_block(settings)
        ),
        fetch_source=_build_settings(
            FetchSourceSettings, settings.get("fetch_source", {})
        ),
        schedule_discovered_links=_build_settings(
            ScheduleDiscoveredLinksSettings,
            settings.get("schedule_discovered_links", {}),
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
