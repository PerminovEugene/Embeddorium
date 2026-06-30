from dataclasses import dataclass
from typing import Optional
from uuid import UUID


def parse_optional_uuid(value) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(value)


def optional_uuid_to_str(value: Optional[UUID]) -> Optional[str]:
    if value is None:
        return None
    return str(value)


@dataclass(frozen=True)
class ProcessLinkSourcePayload:
    url: str
    group: str
    parent_chunk_id: Optional[UUID] = None
    parent_document_id: Optional[UUID] = None
    # Propagated through the entire pipeline so actors load config by run id.
    pipeline_id: Optional[str] = None

    def to_actor_kwargs(self) -> dict:
        return {
            "url": self.url,
            "group": self.group,
            "parent_document_id": optional_uuid_to_str(self.parent_document_id),
            "parent_chunk_id": optional_uuid_to_str(self.parent_chunk_id),
            "pipeline_id": self.pipeline_id,
        }

    @classmethod
    def from_actor_kwargs(
        cls,
        *,
        url: str,
        group: str,
        parent_document_id=None,
        parent_chunk_id=None,
        pipeline_id: Optional[str] = None,
    ) -> "ProcessLinkSourcePayload":
        return cls(
            url=url,
            group=group,
            parent_document_id=parse_optional_uuid(parent_document_id),
            parent_chunk_id=parse_optional_uuid(parent_chunk_id),
            pipeline_id=pipeline_id,
        )
