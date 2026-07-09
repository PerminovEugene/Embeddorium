from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class ChunkDocumentSettings(BaseModel):
    """Settings consumed by the ``chunk_document`` actor.

    ``chunker`` selects a chunker plugin by its registry name (see
    ``backend/plugins/chunkers``, discovered by
    ``backend.plugins.chunkers.registry``). ``settings`` carries that
    chunker's declared field values verbatim — snake_case keys, shape is
    entirely chunker-specific — and is handed straight to
    ``registry.build_chunker`` without reinterpretation. Old runs recorded
    the pre-plugin ``strategy``/``chunk_size``/``chunk_overlap`` shape;
    pydantic silently drops those unknown keys and falls back to these
    defaults, which is acceptable while the product is in beta.
    """

    chunker: str = "text_markdown"
    settings: Dict[str, Any] = Field(default_factory=dict)


class VectorStoreSettings(BaseModel):
    """Settings for the Qdrant collection vectors are upserted into.

    ``similarity`` mirrors the ``Distance`` enum used in
    ``VectorStore.create_collection``.
    """

    collection: str
    similarity: Literal["cosine", "dot", "euclid"]


class EmbedChunksSettings(BaseModel):
    """Settings consumed by the ``embed_chunks`` actor.

    ``provider`` is the full JSON snapshot (``model_dump(mode="json")``) of
    whichever ``Provider`` (Ollama/Remote/Mock) was selected at run-creation
    time.  Storing it here rather than at the top level of ``PipelineRun``
    keeps provider config co-located with the actor that uses it, and leaves
    room for other actors to carry their own provider snapshots independently.
    """

    provider: Dict


class ParseSourceSettings(BaseModel):
    """Settings consumed by the ``parse_source`` actor.

    ``parser`` forces a specific parser instead of selecting one by content
    type. ``"auto"`` keeps the content-type-driven default.
    """

    parser: str = "auto"


class ScheduleEmbeddingsSettings(BaseModel):
    """Settings consumed by the ``schedule_embeddings`` actor.

    ``batch_size`` is the number of chunks per emitted embed job.
    """

    batch_size: int = 32


class ValidateSourceSettings(BaseModel):
    """Settings consumed by the ``validate_source`` actor (both strategies).

    ``normalize_urls`` toggles URL normalization before dedup (web strategy
    only — local file paths are always resolved to their absolute form);
    ``dedup`` toggles the already-queued gate for both strategies.
    """

    normalize_urls: bool = True
    dedup: bool = True


class FetchSourceSettings(BaseModel):
    """Settings consumed by the merged ``fetch_source`` actor.

    Web strategy: ``verify_tls`` toggles TLS verification; ``timeout_seconds``
    is the read timeout; ``allowed_content_types`` is an optional
    comma-separated allowlist that further restricts the
    parser-registry-supported types. Empty means "no extra restriction" — the
    parser registry alone decides what is supported.

    Local-file strategy: ``file_glob`` selects which files a folder seed
    enumerates (applied at seed time, not in the actor).
    """

    verify_tls: bool = True
    timeout_seconds: int = 30
    allowed_content_types: str = ""
    file_glob: str = "*.xml"


class ScheduleDiscoveredLinksSettings(BaseModel):
    """Settings consumed by the ``schedule_discovered_links`` actor.

    ``follow_child_links`` gates whether discovered links are scheduled back to
    the frontier at all. ``follow_cross_domain`` / ``max_depth`` are stored for
    crawl-scope features that overlap the dormant dataset-level fields and are
    not yet enforced.
    """

    follow_child_links: bool = True
    follow_cross_domain: bool = False
    max_depth: int = 3


class FilterDocumentsSettings(BaseModel):
    """Settings consumed by the ``filter_documents`` actor.

    ``enabled`` toggles the relevance gate (when off, every document passes
    through). ``keywords`` is an optional comma-separated list of keywords; an
    empty string means no keyword restriction — all documents pass through.
    When enabled with a non-empty keyword list, only documents whose title (or
    body when the title is absent) contains at least one keyword are advanced.
    """

    enabled: bool = True
    keywords: str = ""


class PipelineActorConfigs(BaseModel):
    """Per-actor configuration for an ingestion pipeline run.

    Groups the non-provider knobs by actor: ``chunk_document`` controls
    text splitting; ``vector_store`` names the Qdrant collection and its
    distance metric; ``embed_chunks`` carries the embedding provider snapshot
    (``EmbedChunksSettings.provider``) so provider config lives next to the
    actor that consumes it.

    The remaining per-actor blocks are optional with sensible defaults, so
    runs created before they existed (and runs whose dataset never exercises a
    given chain) still validate and read defaults.
    """

    chunk_document: ChunkDocumentSettings
    vector_store: VectorStoreSettings
    embed_chunks: EmbedChunksSettings
    parse_source: ParseSourceSettings = Field(default_factory=ParseSourceSettings)
    schedule_embeddings: ScheduleEmbeddingsSettings = Field(
        default_factory=ScheduleEmbeddingsSettings
    )
    validate_source: ValidateSourceSettings = Field(
        default_factory=ValidateSourceSettings
    )
    fetch_source: FetchSourceSettings = Field(default_factory=FetchSourceSettings)
    schedule_discovered_links: ScheduleDiscoveredLinksSettings = Field(
        default_factory=ScheduleDiscoveredLinksSettings
    )
    filter_documents: FilterDocumentsSettings = Field(
        default_factory=FilterDocumentsSettings
    )


class PipelineRun(BaseModel):
    """A saved launch configuration of one ingestion/RAG pipeline run.

    Stores a full snapshot of the dataset at run-creation time so the run is
    self-contained: actors can reconstruct exactly the settings used without
    re-reading global env config, and the DB-search UI can list runs with all
    relevant metadata without extra joins.

    The embedding provider snapshot is stored inside
    ``actor_configs.embed_chunks.provider`` (via ``EmbedChunksSettings``)
    rather than at the top level, because provider is an ``embed_chunks``
    concern — other actors may have their own provider configs in the future.

    Fields
    ------
    id
        Auto-assigned UUID primary key; ``None`` before the row is persisted.
    dataset
        JSON snapshot of the ``Dataset`` (web or local) this run ingests —
        captured via ``model_dump(mode="json")`` so the record survives
        schema drift.
    actor_configs
        Per-actor configuration: chunk_document + vector_store +
        embed_chunks (which carries the provider snapshot).
        Stored as an opaque dict (JSONB) but shaped by ``PipelineActorConfigs``.
    status
        Lifecycle state of the run (pending → running → completed/failed).
    started_at
        Set to ``now()`` when the first seed message is published.
    finished_at
        Set by ``track_pipeline_status`` when the run auto-completes (all
        embed batches finished and no crawl targets remain active).
    created_at
        Set by the database server on insert.
    embeddings_scheduled
        Total embed batches emitted by ``schedule_embeddings`` for this run,
        incremented exactly once per batch (see ``UnitOfWork.add_outbox``).
    embeddings_completed
        Total embed batches finished by ``embed_chunks`` for this run,
        incremented exactly once per batch. ``track_pipeline_status`` compares
        this against ``embeddings_scheduled`` to detect completion.
    """

    id: Optional[uuid.UUID] = None

    # User-supplied display name for the run.
    name: Optional[str] = None

    # Full Dataset snapshot (model_dump of WebDataset/LocalDataset).
    dataset: Dict
    # Shaped as PipelineActorConfigs, stored as an opaque dict.
    # actor_configs.embed_chunks.provider holds the Provider snapshot.
    actor_configs: Dict

    status: Literal["pending", "running", "completed", "failed"] = "pending"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Embed-batch progress counters used by track_pipeline_status to detect
    # run completion; see the class docstring. Old rows lack these columns
    # pre-migration 022, so the DB server default and this model default both
    # fall back to 0.
    embeddings_scheduled: int = 0
    embeddings_completed: int = 0
