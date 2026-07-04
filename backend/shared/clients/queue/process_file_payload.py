from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProcessFileSourcePayload:
    file_path: str
    # Propagated through the entire pipeline so actors load config by run id.
    pipeline_id: Optional[str] = None

    def to_actor_kwargs(self) -> dict:
        return {
            "file_path": self.file_path,
            "pipeline_id": self.pipeline_id,
        }

    @classmethod
    def from_actor_kwargs(
        cls,
        *,
        file_path: str,
        pipeline_id: Optional[str] = None,
    ) -> "ProcessFileSourcePayload":
        return cls(
            file_path=str(file_path),
            pipeline_id=pipeline_id,
        )
