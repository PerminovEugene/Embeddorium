"""Embeddorium MCP server — the RAG lifecycle exposed as agent tools.

This server is a **thin HTTP client of the Embeddorium FastAPI server**
(``backend/server/main.py``). It mirrors, endpoint for endpoint, what the React
UI does: create a web dataset, create a pipeline run bound to an embedding
provider, launch it, poll its status, and search the resulting knowledge base.
It deliberately imports **no** ``SqlStore``/``VectorStore`` and never talks to
Postgres, Qdrant, or RabbitMQ directly — the FastAPI server owns all of that.

Transport is streamable-HTTP bound to ``0.0.0.0`` so agents running in other
containers can connect. Configuration is read once at import from the
environment:

* ``SERVER_URL`` — base URL of the FastAPI server (default
  ``http://server:8000``).
* ``MCP_PORT`` — port this MCP server listens on (default ``8080``).

Agents connect at ``http://<host>:<MCP_PORT>/mcp``.

Wire-format note: the FastAPI server speaks camelCase on request/response
bodies (``sourceType``, ``datasetId``, ``actorSettings``, ``topK`` ...). Provider
``config`` blobs are the one exception and stay snake_case. The payloads built
here match those contracts exactly.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Config, read once at import. Hosts/ports are never hardcoded elsewhere.
SERVER_URL = os.environ.get("SERVER_URL", "http://server:8000").rstrip("/")
MCP_PORT = int(os.environ.get("MCP_PORT", "8080"))

# The provider ``modelType`` literal for embedders (see
# ``backend/shared/models/provider.py::ModelType``). Only providers of this
# capability can drive the ``embed_chunks`` actor.
EMBEDDING_MODEL_TYPE = "embedding"

mcp = FastMCP("Embeddorium")

# One shared HTTP client: its connection pool is reused across tool calls.
# A generous timeout covers launch/search round-trips without hanging forever.
_client = httpx.Client(base_url=SERVER_URL, timeout=httpx.Timeout(30.0))


class ServerError(RuntimeError):
    """A call to the FastAPI server failed.

    Carries a message that surfaces the server's own ``detail`` (for 4xx/5xx)
    or the underlying transport error, so the agent sees exactly what went
    wrong instead of an opaque stack trace.
    """


def _detail(response: httpx.Response) -> str:
    """Best-effort extraction of a human-readable error from a response.

    FastAPI returns ``{"detail": ...}`` on ``HTTPException``; fall back to the
    raw body when the response is not the expected JSON shape.
    """
    try:
        body = response.json()
    except ValueError:
        return response.text.strip() or response.reason_phrase
    if isinstance(body, dict) and "detail" in body:
        return str(body["detail"])
    return str(body)


def _request(method: str, path: str, *, json: Any | None = None) -> Any:
    """Issue one HTTP request to the FastAPI server and return the parsed body.

    Raises :class:`ServerError` with the server's ``detail`` on any non-2xx
    response, and on transport failures (server unreachable, timeout). ``None``
    is returned for empty ``204``-style bodies.
    """
    try:
        response = _client.request(method, path, json=json)
    except httpx.RequestError as exc:
        raise ServerError(
            f"Could not reach the Embeddorium server at {SERVER_URL}{path}: {exc}"
        ) from exc

    if response.is_error:
        raise ServerError(
            f"{method} {path} failed ({response.status_code}): {_detail(response)}"
        )

    if not response.content:
        return None
    return response.json()


def _resolve_embedding_provider(embedding_provider_id: str | None) -> str:
    """Return the id of the embedding provider a run should use.

    If ``embedding_provider_id`` is given it is used verbatim. Otherwise the
    first embedding-type provider from ``GET /providers`` is chosen. Raises
    :class:`ServerError` with actionable guidance when none exists.
    """
    if embedding_provider_id:
        return embedding_provider_id

    providers = _embedding_providers()
    if not providers:
        raise ServerError(
            "No embedding provider is configured. Create one via the "
            "Embeddorium UI (or the /providers API) and pass its id as "
            "`embedding_provider_id`. Use `list_embedding_providers()` to see "
            "the available ones."
        )
    return str(providers[0]["id"])


def _embedding_providers() -> list[dict[str, Any]]:
    """Fetch every provider and keep only the embedding-type ones."""
    providers = _request("GET", "/providers") or []
    return [p for p in providers if p.get("modelType") == EMBEDDING_MODEL_TYPE]


@mcp.tool()
def list_embedding_providers() -> list[dict[str, Any]]:
    """List the configured embedding providers you can build a knowledge base with.

    A knowledge base needs an embedding provider to turn text chunks into
    vectors. This returns only providers whose ``modelType`` is ``"embedding"``
    (chat/reranker/cross-encoder providers are filtered out), each as
    ``{id, name, providerType, modelType, config, createdAt}``.

    Pass one of these ``id`` values as ``embedding_provider_id`` to
    ``create_knowledge_base``. If the list is empty, no embedding provider is
    configured yet — create one in the Embeddorium UI first.
    """
    return _embedding_providers()


@mcp.tool()
def create_knowledge_base(
    name: str,
    source_url: str,
    embedding_provider_id: str | None = None,
) -> dict[str, Any]:
    """Create and launch a knowledge base by crawling and embedding a URL.

    This runs the full ingest pipeline: it registers a web dataset for
    ``source_url``, creates a pipeline run bound to an embedding provider, and
    launches it. Embedding happens asynchronously — the returned ``status`` will
    be ``"running"``; poll ``get_knowledge_base_status(run_id)`` until it reads
    ``"completed"`` before searching.

    ``source_url`` must be a **crawlable** URL. Documentation sites work well
    (the crawler follows links from the seed page). Whole-repository GitHub
    ingestion depends on what the crawl actor can reach from the seed page and
    is not guaranteed.

    Args:
        name: Human-readable name for the knowledge base / run.
        source_url: Seed URL to crawl and ingest.
        embedding_provider_id: Id of the embedding provider to use. When
            omitted, the first available embedding-type provider is chosen
            automatically; if none exists an error explains how to add one.

    Returns:
        ``{run_id, status, name, dataset_id, embedding_provider_id}`` for the
        launched run.
    """
    provider_id = _resolve_embedding_provider(embedding_provider_id)

    dataset = _request(
        "POST",
        "/datasets",
        json={"name": name, "sourceType": "web", "url": source_url},
    )
    dataset_id = str(dataset["id"])

    run = _request(
        "POST",
        "/pipeline-runs",
        json={
            "name": name,
            "datasetId": dataset_id,
            # embed_chunks.providerId is required for every run; other actor
            # blocks are left empty so the server applies its defaults.
            "actorSettings": {"embed_chunks": {"providerId": provider_id}},
        },
    )
    run_id = str(run["id"])

    launched = _request("POST", f"/pipeline-runs/{run_id}/launch")

    return {
        "run_id": run_id,
        "status": launched.get("status", run.get("status")),
        "name": launched.get("name", name),
        "dataset_id": dataset_id,
        "embedding_provider_id": provider_id,
    }


@mcp.tool()
def get_knowledge_base_status(run_id: str) -> dict[str, Any]:
    """Check ingest progress for a knowledge base so you know when it's searchable.

    Fetches the pipeline run and returns its lifecycle ``status`` plus chunk
    counts. Poll this after ``create_knowledge_base`` until ``status`` is
    ``"completed"`` before calling ``search_knowledge_base``.

    Args:
        run_id: The run id returned by ``create_knowledge_base``.

    Returns:
        ``{run_id, name, status, chunks_embedded, chunks_pending, started_at,
        finished_at}``. ``status`` is one of ``pending`` | ``running`` |
        ``completed`` | ``failed``. While ``running``, ``chunks_pending`` counts
        down as ``chunks_embedded`` rises.
    """
    run = _request("GET", f"/pipeline-runs/{run_id}")
    return {
        "run_id": str(run["id"]),
        "name": run.get("name"),
        "status": run.get("status"),
        "chunks_embedded": run.get("chunksEmbedded", 0),
        "chunks_pending": run.get("chunksPending", 0),
        "started_at": run.get("startedAt"),
        "finished_at": run.get("finishedAt"),
    }


@mcp.tool()
def search_knowledge_base(
    run_id: str,
    query: str,
    top_k: int = 5,
    method: str = "semantic",
) -> list[dict[str, Any]]:
    """Retrieve the most relevant chunks from a knowledge base for a query.

    This is the actual RAG query. It searches the embeddings produced by the
    given run and returns hits enriched with chunk text and source-document
    metadata, ordered best-first (a hit's list index is its rank).

    The knowledge base must have finished ingesting — check
    ``get_knowledge_base_status(run_id)`` reads ``"completed"`` first, otherwise
    results may be empty or partial.

    Args:
        run_id: The run id of the knowledge base to search.
        query: Natural-language query text.
        top_k: Maximum number of hits to return (default 5).
        method: Retrieval strategy — ``"semantic"`` (dense vectors, the
            default), ``"keyword"`` (BM25 sparse), or ``"hybrid"`` (dense + BM25
            fused via reciprocal rank fusion).

    Returns:
        A list of hit objects as returned by the server (chunk text, score, and
        source-document fields).
    """
    result = _request(
        "POST",
        "/search",
        json={
            "configuration": {
                "runId": run_id,
                "topK": top_k,
                "searchMethod": method,
            },
            "source": {"inputs": [{"id": "query", "text": query}]},
        },
    )
    return result if isinstance(result, list) else [result]


@mcp.tool()
def list_knowledge_bases() -> list[dict[str, Any]]:
    """List every knowledge base (pipeline run), newest first.

    Use this to discover existing knowledge bases and their ``run_id`` values so
    you can search them or check their status. Each entry is summarized as
    ``{run_id, name, status, dataset_name, created_at}``.

    Args:
        (none)

    Returns:
        A list of knowledge-base summaries. To search one, pass its ``run_id``
        to ``search_knowledge_base``.
    """
    runs = _request("GET", "/pipeline-runs") or []
    summaries: list[dict[str, Any]] = []
    for run in runs:
        dataset = run.get("dataset") or {}
        summaries.append(
            {
                "run_id": str(run["id"]),
                "name": run.get("name"),
                "status": run.get("status"),
                "dataset_name": dataset.get("name"),
                "created_at": run.get("createdAt"),
            }
        )
    return summaries


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info(
        "Starting Embeddorium MCP server on 0.0.0.0:%s (server=%s)",
        MCP_PORT,
        SERVER_URL,
    )
    # streamable-HTTP bound to 0.0.0.0 so agents in other containers can reach
    # it at http://<host>:<MCP_PORT>/mcp.
    mcp.run(transport="streamable-http", host="0.0.0.0", port=MCP_PORT, path="/mcp")
