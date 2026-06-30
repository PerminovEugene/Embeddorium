"""Typed payloads for the inter-stage messages of the ingestion pipeline.

Every stage after ``fetch_source`` is driven by the crawl target id plus its
crawl group; the stage looks up whatever else it needs (source fetch, document,
chunks) from the store. Keeping the wire payload minimal avoids carrying large
or stale data through RabbitMQ.

``pipeline_id`` is threaded through every payload so each actor can load the
run's saved configuration (provider/model, chunk settings, collection name) by
id instead of falling back to global env config.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class _CrawlStagePayload:
    crawl_target_id: UUID
    group: str
    # Propagated from the seed message so actors read config by run id.
    pipeline_id: Optional[str] = None

    def to_actor_kwargs(self) -> dict:
        return {
            "crawl_target_id": str(self.crawl_target_id),
            "group": str(self.group),
            "pipeline_id": self.pipeline_id,
        }

    @classmethod
    def from_actor_kwargs(
        cls,
        *,
        crawl_target_id: str,
        group: str,
        pipeline_id: Optional[str] = None,
    ):
        return cls(
            crawl_target_id=UUID(crawl_target_id),
            group=str(group),
            pipeline_id=pipeline_id,
        )


@dataclass(frozen=True)
class FilterTaxActsPayload(_CrawlStagePayload):
    pass


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
