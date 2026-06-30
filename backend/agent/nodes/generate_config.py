from __future__ import annotations

import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agent.nodes.base import Node, format_chunks
from backend.agent.state import AgentState

_SYSTEM = (
    "You are a tax law config builder. "
    "Using ONLY the provided chunks, build a JSON object that conforms to the target schema. "
    "Do not invent data not present in the chunks. "
    "If a field has no data in the chunks, set it to null. "
    "Output only valid JSON, no prose or markdown fences."
)


class GenerateConfigNode(Node):
    name = "generate_config"

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    def __call__(self, state: AgentState) -> dict:
        missing = state.get("missing_fields") or []
        is_partial = bool(missing)
        warnings = [f"Partial config: no data found for fields {missing}"] if is_partial else []

        response = self._llm.invoke([
            SystemMessage(_SYSTEM),
            HumanMessage(
                f"Country: {state['country']}, Year: {state['year']}\n"
                f"Target schema: {json.dumps(state.get('target_schema', {}))}\n\n"
                f"Chunks:\n{format_chunks(state.get('chunks', []))}"
            ),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            config = json.loads(raw)
        except json.JSONDecodeError:
            config = {"raw": raw}

        return {"config": config, "is_partial": is_partial, "warnings": warnings}
