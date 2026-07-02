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
class FilterDocumentsPayload(_CrawlStagePayload):
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


@dataclass(frozen=True)
class TrackPipelineStatusPayload:
    """Message that pokes ``track_pipeline_status`` to re-check a run.

    Unlike the crawl-stage payloads above this carries no target/group — the
    tracker only needs the run id to re-derive completion from the DB
    (``crawl_targets`` + the run's own embed counters), so the wire message
    stays minimal.
    """

    pipeline_id: UUID

    def to_actor_kwargs(self) -> dict:
        return {"pipeline_id": str(self.pipeline_id)}

    @classmethod
    def from_actor_kwargs(cls, *, pipeline_id: str) -> "TrackPipelineStatusPayload":
        return cls(pipeline_id=UUID(pipeline_id))
