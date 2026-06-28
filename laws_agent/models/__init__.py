from laws_agent.models.document import Document
from laws_agent.models.document_chunk import DocumentChunk
from laws_agent.models.crawl_target import CrawlTarget, CrawlTargetStatus
from laws_agent.models.source_fetch import SourceFetch
from laws_agent.models.discovered_link import DiscoveredLink, DiscoveredLinkStatus
from laws_agent.models.outbox_event import OutboxEvent, OutboxStatus
from laws_agent.models.pipeline_run import (
    ChunkDocumentSettings,
    EmbedChunksSettings,
    PipelineRun,
    PipelineSettings,
    VectorStoreSettings,
)

# Resolve forward references created by TYPE_CHECKING guards
Document.model_rebuild()
DocumentChunk.model_rebuild()

__all__ = [
    "Document",
    "DocumentChunk",
    "CrawlTarget",
    "CrawlTargetStatus",
    "SourceFetch",
    "DiscoveredLink",
    "DiscoveredLinkStatus",
    "OutboxEvent",
    "OutboxStatus",
    "PipelineRun",
    "PipelineSettings",
    "ChunkDocumentSettings",
    "EmbedChunksSettings",
    "VectorStoreSettings",
]
