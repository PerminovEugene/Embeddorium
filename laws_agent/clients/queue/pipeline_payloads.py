"""Typed payloads for the inter-stage messages of the ingestion pipeline.

Every stage after ``fetch_source`` is driven by the crawl target id plus its
crawl group; the stage looks up whatever else it needs (source fetch, document,
chunks) from the store. Keeping the wire payload minimal avoids carrying large
or stale data through RabbitMQ.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class _CrawlStagePayload:
    crawl_target_id: UUID
    group: str

    def to_actor_kwargs(self) -> dict:
        return {
            "crawl_target_id": str(self.crawl_target_id),
            "group": str(self.group),
        }

    @classmethod
    def from_actor_kwargs(cls, *, crawl_target_id: str, group: str):
        return cls(crawl_target_id=UUID(crawl_target_id), group=str(group))


@dataclass(frozen=True)
class ParseSourcePayload(_CrawlStagePayload):
    pass


@dataclass(frozen=True)
class ChunkDocumentPayload(_CrawlStagePayload):
    pass


@dataclass(frozen=True)
class ScheduleEmbeddingsPayload(_CrawlStagePayload):
    pass


@dataclass(frozen=True)
class ScheduleDiscoveredLinksPayload(_CrawlStagePayload):
    pass
