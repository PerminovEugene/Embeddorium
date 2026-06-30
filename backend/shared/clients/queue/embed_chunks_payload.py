from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID


@dataclass(frozen=True)
class EmbedChunksPayload:
    document_id: UUID
    chunk_ids: List[UUID]
    group: str
    # Propagated from the seed message so the embed actor reads config by run id.
    pipeline_id: Optional[str] = None

    def to_actor_kwargs(self) -> dict:
        return {
            "document_id": str(self.document_id),
            "chunk_ids": [str(chunk_id) for chunk_id in self.chunk_ids],
            "group": str(self.group),
            "pipeline_id": self.pipeline_id,
        }

    @classmethod
    def from_actor_kwargs(
        cls,
        *,
        document_id: str,
        chunk_ids: List[str],
        group: str,
        pipeline_id: Optional[str] = None,
    ) -> "EmbedChunksPayload":
        return cls(
            document_id=UUID(document_id),
            chunk_ids=[UUID(chunk_id) for chunk_id in chunk_ids],
            group=str(group),
            pipeline_id=pipeline_id,
        )
