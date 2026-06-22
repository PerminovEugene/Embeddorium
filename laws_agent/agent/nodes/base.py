from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from laws_agent.agent.state import AgentState


class Node(ABC):
    name: ClassVar[str]

    @abstractmethod
    def __call__(self, state: AgentState) -> dict: ...


def format_chunks(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[{i + 1}] (score={c.get('score', 'n/a')}) {c.get('text', '')}"
        for i, c in enumerate(chunks)
    )
