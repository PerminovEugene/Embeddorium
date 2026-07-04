from __future__ import annotations

import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agent.nodes.base import Node, format_chunks
from backend.agent.state import AgentState

_SYSTEM = (
    "You are a coverage checker. "
    "Given a target schema (fields to populate) and retrieved chunks, "
    "determine if there is enough information to fill all schema fields. "
    "Output JSON: {\"coverage_ok\": bool, \"missing_fields\": [list of field names lacking data]}. "
    "Output only valid JSON, no prose."
)


class CheckCoverageNode(Node):
    name = "check_coverage"

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    def __call__(self, state: AgentState) -> dict:
        response = self._llm.invoke([
            SystemMessage(_SYSTEM),
            HumanMessage(
                f"Country: {state['country']}, Year: {state['year']}\n"
                f"Target schema fields: {list(state.get('target_schema', {}).keys())}\n\n"
                f"Chunks:\n{format_chunks(state.get('chunks', []))}"
            ),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            result = json.loads(raw)
            coverage_ok = bool(result.get("coverage_ok", False))
            missing_fields = result.get("missing_fields") or []
        except json.JSONDecodeError:
            coverage_ok = False
            missing_fields = list(state.get("target_schema", {}).keys())
        return {"coverage_ok": coverage_ok, "missing_fields": missing_fields}
