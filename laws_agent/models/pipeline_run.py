from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ChunkDocumentSettings(BaseModel):
    """Settings consumed by the ``chunk_document`` actor.

    Mirror of ``TextSplitter``'s ``MarkdownTextSplitter(chunk_size=...,
    chunk_overlap=...)`` configuration.
    """

    strategy: str
    chunk_size: int
    chunk_overlap: int


class EmbedChunksSettings(BaseModel):
    """Settings consumed by the ``embed_chunks`` actor.

    Mirror of ``EMBED_PROVIDER`` / ``OLLAMA_EMBED_MODEL`` / ``MOCK_EMBED_DIM``.
    ``mock_dim`` is only set when ``provider == "mock"``.
    """

    provider: Literal["huggingface", "ollama", "mock"]
    model: str
    mock_dim: Optional[int] = None


class VectorStoreSettings(BaseModel):
    """Settings for the Qdrant collection vectors are upserted into.

    ``similarity`` mirrors the ``Distance`` enum used in
    ``VectorStore.create_collection``.
    """

    collection: str
    similarity: Literal["cosine", "dot", "euclid"]


class PipelineSettings(BaseModel):
    """Per-actor launch settings, grouped by the pipeline actor that consumes
    them (see README "Pipeline flow")."""

    chunk_document: ChunkDocumentSettings
    embed_chunks: EmbedChunksSettings
    vector_store: VectorStoreSettings


class PipelineRun(BaseModel):
    """A saved launch configuration of one ingestion/RAG pipeline run.

    Captures everything needed to reproduce or compare a run: the dataset it
    targeted (``group``/``source_type``/``collection_name``) plus the
    per-actor ``settings`` used along the pipeline chain.
    """

    id: Optional[uuid.UUID] = None

    group: str
    source_type: Literal["web", "xml"] = "web"
    collection_name: str

    settings: PipelineSettings

    created_at: Optional[datetime] = None
