from dataclasses import dataclass
from uuid import UUID


def parse_optional_uuid(value: str | UUID | None) -> UUID | None:
    if value is None:
        return None

    if isinstance(value, UUID):
        return value

    return UUID(value)


def optional_uuid_to_str(value: UUID | None) -> str | None:
    if value is None:
        return None

    return str(value)


@dataclass(frozen=True)
class ProcessLinkSourcePayload:
    url: str
    group: str
    parent_chunk_id: UUID | None = None
    parent_document_id: UUID | None = None

    def to_actor_kwargs(self) -> dict:
        return {
            "url": self.url,
            "group": self.group,
            "parent_document_id": optional_uuid_to_str(self.parent_document_id),
            "parent_chunk_id": optional_uuid_to_str(self.parent_chunk_id),
        }

    @classmethod
    def from_actor_kwargs(
        cls,
        *,
        url: str,
        group: str,
        parent_document_id: str | UUID | None = None,
        parent_chunk_id: str | UUID | None = None,
    ) -> "ProcessLinkSourcePayload":
        return cls(
            url=url,
            group=group,
            parent_document_id=parse_optional_uuid(parent_document_id),
            parent_chunk_id=parse_optional_uuid(parent_chunk_id),
        )