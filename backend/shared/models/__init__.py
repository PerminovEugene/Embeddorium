from backend.shared.models.document import Document
from backend.shared.models.document_chunk import DocumentChunk
from backend.shared.models.crawl_target import CrawlTarget, CrawlTargetStatus
from backend.shared.models.dataset import Dataset, LocalDataset, WebDataset
from backend.shared.models.source_fetch import SourceFetch
from backend.shared.models.discovered_link import DiscoveredLink, DiscoveredLinkStatus
from backend.shared.models.outbox_event import OutboxEvent, OutboxStatus
from backend.shared.models.pipeline_run import (
    ChunkDocumentSettings,
    EmbedChunksSettings,
    FetchSourceSettings,
    FilterDocumentsSettings,
    ParseSourceSettings,
    PipelineActorConfigs,
    PipelineRun,
    ScheduleDiscoveredLinksSettings,
    ScheduleEmbeddingsSettings,
    ValidateSourceSettings,
    VectorStoreSettings,
)
from backend.shared.models.provider import (
    MockProvider,
    ModelType,
    OllamaProvider,
    Provider,
    RemoteProvider,
)
from backend.shared.models.search import Search
from backend.shared.models.search_input import SearchInput

# Resolve forward references created by TYPE_CHECKING guards
Document.model_rebuild()
DocumentChunk.model_rebuild()

__all__ = [
    "Document",
    "DocumentChunk",
    "CrawlTarget",
    "CrawlTargetStatus",
    "Dataset",
    "WebDataset",
    "LocalDataset",
    "SourceFetch",
    "DiscoveredLink",
    "DiscoveredLinkStatus",
    "OutboxEvent",
    "OutboxStatus",
    "PipelineRun",
    "PipelineActorConfigs",
    "ChunkDocumentSettings",
    "EmbedChunksSettings",
    "VectorStoreSettings",
    "ParseSourceSettings",
    "ScheduleEmbeddingsSettings",
    "ValidateSourceSettings",
    "FetchSourceSettings",
    "ScheduleDiscoveredLinksSettings",
    "FilterDocumentsSettings",
    "Provider",
    "OllamaProvider",
    "RemoteProvider",
    "MockProvider",
    "ModelType",
    "Search",
    "SearchInput",
]
