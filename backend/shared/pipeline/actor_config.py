"""Load a pipeline run's per-actor settings at actor runtime.

Mirrors the caching pattern already used by the chunk/embed launchers: a
``PipelineRun`` snapshot is immutable after creation, so each actor process
loads a run's ``actor_configs`` from the DB once per ``pipeline_id`` and reuses
the parsed :class:`PipelineActorConfigs` for every subsequent message of that
run instead of re-querying.

Returns ``None`` when ``pipeline_id`` is absent (legacy messages), the run row
is missing, or the snapshot can't be parsed — callers then fall back to the
settings models' own defaults, so an actor never hard-fails on config loading.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from backend.shared.models import PipelineActorConfigs
from backend.shared.storage.sql.sql_store import SqlStore

logger = logging.getLogger(__name__)

# Parsed configs cached by pipeline_id. Per-process and never stale within a
# run (the snapshot is immutable once created).
_configs: dict[str, PipelineActorConfigs] = {}


def load_actor_configs(
    store: SqlStore, pipeline_id: Optional[str]
) -> Optional[PipelineActorConfigs]:
    """Return this run's parsed ``PipelineActorConfigs`` (cached), or ``None``.

    ``None`` signals "no run-specific config" so the caller uses defaults.
    """
    if not pipeline_id:
        return None

    key = str(pipeline_id)
    cached = _configs.get(key)
    if cached is not None:
        return cached

    try:
        run = store.pipeline_runs.get(uuid.UUID(key))
    except (ValueError, TypeError):
        return None
    if run is None:
        return None

    try:
        cfg = PipelineActorConfigs.model_validate(run.actor_configs)
    except Exception:
        logger.warning(
            "could not parse actor_configs for pipeline_id=%s", key
        )
        return None

    _configs[key] = cfg
    return cfg
