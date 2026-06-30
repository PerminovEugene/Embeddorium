from __future__ import annotations

import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agent.nodes.base import Node, format_chunks
from backend.agent.state import AgentState

_SYSTEM = (
    "You are a JSON repair assistant. "
    "Fix the provided JSON config to resolve the schema validation errors. "
    "Use only information from the provided chunks — do not invent data. "
    "Output only valid JSON, no prose or markdown fences."
)


class RepairConfigNode(Node):
    name = "repair_config"

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    def __call__(self, state: AgentState) -> dict:
        response = self._llm.invoke([
            SystemMessage(_SYSTEM),
            HumanMessage(
                f"Current config:\n{json.dumps(state.get('config') or {}, indent=2)}\n\n"
                f"Validation errors: {state.get('validation_errors', [])}\n\n"
                f"Target schema: {json.dumps(state.get('target_schema') or {})}\n\n"
                f"Chunks:\n{format_chunks(state.get('chunks', []))}"
            ),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            config = json.loads(raw)
        except json.JSONDecodeError:
            config = state.get("config") or {}
        return {
            "config": config,
            "repair_attempts": state.get("repair_attempts", 0) + 1,
        }
