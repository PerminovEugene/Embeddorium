"""Payload for the ``validate_source`` actor (shared ingestion entry point).

``url`` is either a web URL (web datasets, discovered links) or a local file
path (local datasets) — the actor picks a validation strategy per the run's
dataset source type. ``parent_*`` ids are only set for links discovered while
crawling; local-file messages never carry them.
"""

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
class ValidateSourcePayload:
    url: str
    parent_chunk_id: Optional[UUID] = None
    parent_document_id: Optional[UUID] = None
    # Propagated through the entire pipeline so actors load config by run id.
    pipeline_id: Optional[str] = None

    def to_actor_kwargs(self) -> dict:
        return {
            "url": self.url,
            "parent_document_id": optional_uuid_to_str(self.parent_document_id),
            "parent_chunk_id": optional_uuid_to_str(self.parent_chunk_id),
            "pipeline_id": self.pipeline_id,
        }

    @classmethod
    def from_actor_kwargs(
        cls,
        *,
        url: str,
        parent_document_id=None,
        parent_chunk_id=None,
        pipeline_id: Optional[str] = None,
    ) -> "ValidateSourcePayload":
        return cls(
            url=url,
            parent_document_id=parse_optional_uuid(parent_document_id),
            parent_chunk_id=parse_optional_uuid(parent_chunk_id),
            pipeline_id=pipeline_id,
        )
