from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class ProcessWebSourcePayload:
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
    ) -> "ProcessWebSourcePayload":
        return cls(
            crawl_target_id=UUID(crawl_target_id),
            group=str(group),
            pipeline_id=pipeline_id,
        )
