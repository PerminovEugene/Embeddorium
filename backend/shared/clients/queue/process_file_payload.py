from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProcessFileSourcePayload:
    file_path: str
    group: str
    # Propagated through the entire pipeline so actors load config by run id.
    pipeline_id: Optional[str] = None

    def to_actor_kwargs(self) -> dict:
        return {
            "file_path": self.file_path,
            "group": self.group,
            "pipeline_id": self.pipeline_id,
        }

    @classmethod
    def from_actor_kwargs(
        cls,
        *,
        file_path: str,
        group: str,
        pipeline_id: Optional[str] = None,
    ) -> "ProcessFileSourcePayload":
        return cls(
            file_path=str(file_path),
            group=str(group),
            pipeline_id=pipeline_id,
        )
