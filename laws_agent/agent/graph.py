from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from laws_agent.agent.config import LLMProvider
from laws_agent.agent.mcp_client import get_mcp_tools
from laws_agent.agent.nodes import (
    CheckCoverageNode,
    ExpandChunksNode,
    GenerateConfigNode,
    PlanSearchQueriesNode,
    RepairConfigNode,
    SearchChunksNode,
    ValidateConfigNode,
)
from laws_agent.agent.providers.ollama import build_ollama_llm
from laws_agent.agent.providers.openai import build_openai_llm
from laws_agent.agent.state import AgentState
from laws_agent.storage.sql.sql_store import SqlStore

MAX_SEARCH_ROUNDS = 3
MAX_REPAIR_ATTEMPTS = 1


def _build_llm(provider: LLMProvider, model: str) -> BaseChatModel:
    if provider == "openai":
        return build_openai_llm()
    return build_ollama_llm(model)


def _route_after_coverage(state: AgentState) -> str:
    if state.get("coverage_ok"):
        return GenerateConfigNode.name
    if state.get("search_count", 0) < MAX_SEARCH_ROUNDS:
        return SearchChunksNode.name
    # search limit reached — generate partial config with warnings
    return GenerateConfigNode.name


def _route_after_validate(state: AgentState) -> str:
    if not state.get("validation_errors"):
        return END
    if state.get("repair_attempts", 0) < MAX_REPAIR_ATTEMPTS:
        return RepairConfigNode.name
    return END


def _build_graph(llm: BaseChatModel, search_tool, sql_store: SqlStore):
    nodes = [
        PlanSearchQueriesNode(llm),
        SearchChunksNode(search_tool),
        ExpandChunksNode(sql_store),
        CheckCoverageNode(llm),
        GenerateConfigNode(llm),
        ValidateConfigNode(),
        RepairConfigNode(llm),
    ]

    graph = StateGraph(AgentState)
    for node in nodes:
        graph.add_node(node.name, node)

    graph.add_edge(START, PlanSearchQueriesNode.name)
    graph.add_edge(PlanSearchQueriesNode.name, SearchChunksNode.name)
    graph.add_edge(SearchChunksNode.name, ExpandChunksNode.name)
    graph.add_edge(ExpandChunksNode.name, CheckCoverageNode.name)
    graph.add_conditional_edges(CheckCoverageNode.name, _route_after_coverage)
    graph.add_edge(GenerateConfigNode.name, ValidateConfigNode.name)
    graph.add_conditional_edges(ValidateConfigNode.name, _route_after_validate)
    graph.add_edge(RepairConfigNode.name, ValidateConfigNode.name)

    return graph.compile()


async def build_agent(provider: LLMProvider, model: str | None):
    tools = await get_mcp_tools()
    search_tool = next(t for t in tools if t.name == "search_knowledge_base")
    llm = _build_llm(provider, model)
    sql_store = SqlStore()
    return _build_graph(llm, search_tool, sql_store)
