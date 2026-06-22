from __future__ import annotations

from laws_agent.agent.nodes.base import Node
from laws_agent.agent.state import AgentState
from laws_agent.storage.sql.sql_store import SqlStore


class ExpandChunksNode(Node):
    name = "expand_chunks"

    def __init__(self, sql_store: SqlStore) -> None:
        self._sql_store = sql_store

    def __call__(self, state: AgentState) -> dict:
        base_chunks = list(state["chunks"])
        seen_ids = {c["chunk_id"] for c in base_chunks if c.get("chunk_id")}
        extra: list[dict] = []

        for chunk in state["chunks"]:
            doc_id = chunk.get("document_id")
            idx = chunk.get("chunk_index")
            if doc_id is None or idx is None:
                continue
            for neighbor in self._sql_store.chunks.get_neighbors(doc_id, idx):
                cid = str(neighbor.id)
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                extra.append({
                    "chunk_id": cid,
                    "document_id": str(neighbor.document_id),
                    "chunk_index": neighbor.chunk_index,
                    "text": neighbor.text,
                    "score": None,
                    "title": neighbor.document.title if neighbor.document else None,
                    "source_url": neighbor.document.source_url if neighbor.document else None,
                })

        return {"chunks": base_chunks + extra}
