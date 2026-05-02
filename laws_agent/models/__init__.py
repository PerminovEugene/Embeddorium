from laws_agent.models.document import Document
from laws_agent.models.document_chunk import DocumentChunk
from laws_agent.models.crawl_target import CrawlTarget, CrawlTargetStatus

# Resolve forward references created by TYPE_CHECKING guards
Document.model_rebuild()
DocumentChunk.model_rebuild()

__all__ = ["Document", "DocumentChunk", "CrawlTarget", "CrawlTargetStatus"]
