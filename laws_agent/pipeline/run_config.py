"""Snapshot the pipeline launch configuration as a ``PipelineRun``.

Called at the *beginning* of each ingestion chain (the seed runner, which has
the config file, with the entry actors as a fallback) so the UI's DB-search
mode can later pick a run and reuse exactly the collection + embedding model it
was built with.

Values come from the group's config-file ``settings`` block when present;
anything a group omits falls back to the global env/constant default the actors
use at runtime, so the recorded config can't drift from what the pipeline does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from laws_agent import config
from laws_agent.models import (
    ChunkDocumentSettings,
    EmbedChunksSettings,
    PipelineRun,
    PipelineSettings,
    VectorStoreSettings,
)
from laws_agent.parsers.chunking_config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHUNK_STRATEGY,
)
from laws_agent.parsers.config_parser import (
    EmbedChunksSettingsConfig,
    PipelineSettingsConfig,
)
from laws_agent.storage.vector.collection_naming import (
    COLLECTION_SIMILARITY,
    build_collection_name,
)

if TYPE_CHECKING:
    from laws_agent.storage.sql.sql_store import SqlStore

# Mirrors MODEL_NAME in embed_chunks_actor.handler. Duplicated (not imported)
# because that actor's package __init__ imports its launcher, which builds a
# RabbitMQ broker at import time — importing it here just to read a constant
# would drag that side effect into the frontier-manager worker.
_HUGGINGFACE_EMBED_MODEL = "Qwen/Qwen3-Embedding-8B"


def _embed_settings(
    file_cfg: EmbedChunksSettingsConfig | None,
) -> EmbedChunksSettings:
    """Resolve the embedding provider/model: file config over global env."""
    provider = (
        file_cfg.provider if file_cfg and file_cfg.provider else config.EMBED_PROVIDER
    )
    file_model = file_cfg.model if file_cfg else None

    if provider == "ollama":
        return EmbedChunksSettings(
            provider="ollama", model=file_model or config.OLLAMA_EMBED_MODEL
        )
    if provider == "mock":
        mock_dim = (
            file_cfg.mock_dim
            if file_cfg and file_cfg.mock_dim is not None
            else config.MOCK_EMBED_DIM
        )
        return EmbedChunksSettings(
            provider="mock", model=file_model or "mock", mock_dim=mock_dim
        )
    # Anything else falls back to the real local HuggingFace model, matching
    # get_model_and_size() in the embed handler.
    return EmbedChunksSettings(
        provider="huggingface", model=file_model or _HUGGINGFACE_EMBED_MODEL
    )


def build_pipeline_run(
    *,
    group: str,
    source_type: str,
    settings: PipelineSettingsConfig | None = None,
) -> PipelineRun:
    """Build the launch-config snapshot for *group* / *source_type*.

    *settings* is the group's config-file block (or None); each value overrides
    the corresponding global env/constant default.
    """
    chunk_cfg = settings.chunk_document if settings else None
    vector_cfg = settings.vector_store if settings else None
    embed_cfg = settings.embed_chunks if settings else None

    collection = build_collection_name(group)
    return PipelineRun(
        group=group,
        source_type=source_type,
        collection_name=collection,
        settings=PipelineSettings(
            chunk_document=ChunkDocumentSettings(
                strategy=(
                    chunk_cfg.strategy
                    if chunk_cfg and chunk_cfg.strategy
                    else CHUNK_STRATEGY
                ),
                chunk_size=(
                    chunk_cfg.chunk_size
                    if chunk_cfg and chunk_cfg.chunk_size is not None
                    else CHUNK_SIZE
                ),
                chunk_overlap=(
                    chunk_cfg.chunk_overlap
                    if chunk_cfg and chunk_cfg.chunk_overlap is not None
                    else CHUNK_OVERLAP
                ),
            ),
            embed_chunks=_embed_settings(embed_cfg),
            vector_store=VectorStoreSettings(
                collection=collection,
                similarity=(
                    vector_cfg.similarity
                    if vector_cfg and vector_cfg.similarity
                    else COLLECTION_SIMILARITY
                ),
            ),
        ),
    )


def load_pipeline_run(
    store: SqlStore, group: str, *, source_type: str = "web"
) -> PipelineRun:
    """Return the run recorded for *group* so downstream stages read the config
    their run was started with — not whatever global env config happens to be
    set now.

    Falls back to a fresh snapshot from global config if no run was recorded
    (legacy data, or recording disabled), so the stages never hard-fail on a
    missing row.
    """
    recorded = store.pipeline_runs.get_by_group(group)
    if recorded is not None:
        return recorded
    return build_pipeline_run(group=group, source_type=source_type)
