from __future__ import annotations

from laws_agent.agent.nodes.base import Node
from laws_agent.agent.state import AgentState


class SearchChunksNode(Node):
    name = "search_chunks"

    def __init__(self, search_tool) -> None:
        self._search_tool = search_tool

    def __call__(self, state: AgentState) -> dict:
        existing_ids = {c["chunk_id"] for c in state.get("chunks", []) if c.get("chunk_id")}
        new_chunks: list[dict] = []

        for query in state.get("search_queries", []):
            raw = self._search_tool.invoke({"query": query, "limit": 8})
            if isinstance(raw, list):
                for chunk in raw:
                    cid = chunk.get("chunk_id")
                    if cid and cid not in existing_ids:
                        existing_ids.add(cid)
                        new_chunks.append(chunk)

        return {
            "chunks": list(state.get("chunks", [])) + new_chunks,
            "search_count": state.get("search_count", 0) + 1,
        }
