from __future__ import annotations

import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from laws_agent.agent.nodes.base import Node
from laws_agent.agent.state import AgentState

_SYSTEM = (
    "You are a tax law research assistant. "
    "Given a country, year, and target schema fields, generate a list of specific "
    "search queries to retrieve relevant tax law chunks from a knowledge base. "
    "Output a JSON array of strings, each a concise search query. "
    "Aim for 3-6 queries covering different aspects of the schema. "
    "Output only a valid JSON array, no prose."
)


class PlanSearchQueriesNode(Node):
    name = "plan_search_queries"

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    def __call__(self, state: AgentState) -> dict:
        schema_fields = list(state.get("target_schema", {}).keys())
        response = self._llm.invoke([
            SystemMessage(_SYSTEM),
            HumanMessage(
                f"Country: {state['country']}\n"
                f"Year: {state['year']}\n"
                f"Schema fields to populate: {schema_fields}"
            ),
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            queries = json.loads(raw)
            if not isinstance(queries, list):
                queries = [str(queries)]
        except json.JSONDecodeError:
            queries = [f"{state['country']} {state['year']} tax law"]
        return {"search_queries": queries, "search_count": 0, "chunks": []}
