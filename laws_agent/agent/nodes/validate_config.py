from __future__ import annotations

from laws_agent.agent.nodes.base import Node
from laws_agent.agent.state import AgentState


class ValidateConfigNode(Node):
    name = "validate_config"

    def __call__(self, state: AgentState) -> dict:
        config = state.get("config") or {}
        schema = state.get("target_schema") or {}
        errors = [
            f"missing field: {f}"
            for f in schema
            if f not in config or config[f] is None
        ]
        return {"validation_errors": errors}
