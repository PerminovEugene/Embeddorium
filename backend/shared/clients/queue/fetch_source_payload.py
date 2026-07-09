"""Payload for the merged ``fetch_source`` actor (web fetch or local file read).

The target already exists (created by ``validate_source``), so the wire
message only carries its id plus the run id used to load per-run config.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class FetchSourcePayload:
    crawl_target_id: UUID
    # Propagated from the seed message so actors read config by run id.
    pipeline_id: Optional[str] = None

    def to_actor_kwargs(self) -> dict:
        return {
            "crawl_target_id": str(self.crawl_target_id),
            "pipeline_id": self.pipeline_id,
        }

    @classmethod
    def from_actor_kwargs(
        cls,
        *,
        crawl_target_id: str,
        pipeline_id: Optional[str] = None,
    ) -> "FetchSourcePayload":
        return cls(
            crawl_target_id=UUID(crawl_target_id),
            pipeline_id=pipeline_id,
        )
