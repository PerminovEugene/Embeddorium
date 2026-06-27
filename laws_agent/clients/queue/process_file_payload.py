from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessFileSourcePayload:
    file_path: str
    group: str

    def to_actor_kwargs(self) -> dict:
        return {
            "file_path": self.file_path,
            "group": self.group,
        }

    @classmethod
    def from_actor_kwargs(
        cls,
        *,
        file_path: str,
        group: str,
    ) -> "ProcessFileSourcePayload":
        return cls(
            file_path=str(file_path),
            group=str(group),
        )
