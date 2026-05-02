from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class EmbedChunksPayload:
    document_id: UUID
    chunk_ids: list[UUID]
    group: str

    def to_actor_kwargs(self) -> dict:
        return {
            "document_id": str(self.document_id),
            "chunk_ids": [str(chunk_id) for chunk_id in self.chunk_ids],
            "group": str(self.group)
        }

    @classmethod
    def from_actor_kwargs(
        cls,
        *,
        document_id: str,
        chunk_ids: list[str],
        group: str
    ) -> "EmbedChunksPayload":
        return cls(
            document_id=UUID(document_id),
            chunk_ids=[UUID(chunk_id) for chunk_id in chunk_ids],
            group=str(group)
        )