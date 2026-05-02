from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ProcessWebSourcePayload:
    crawl_target_id: UUID
    group: str

    def to_actor_kwargs(self) -> dict:
        return {
            "crawl_target_id": str(self.crawl_target_id),
            "group": str(self.group),
        }

    @classmethod
    def from_actor_kwargs(
        cls,
        *,
        crawl_target_id: str,
        group: str,
    ) -> "ProcessWebSourcePayload":
        return cls(
            crawl_target_id=UUID(crawl_target_id),
            group=str(group),
        )
