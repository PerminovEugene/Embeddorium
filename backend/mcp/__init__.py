"""Embeddorium MCP server package.

Exposes the RAG lifecycle (ingest → embed → search) as MCP tools for external
agents. The server is a thin HTTP client of the FastAPI server, mirroring how
the React UI drives the same endpoints — it never touches Postgres/Qdrant/
RabbitMQ directly. See ``backend/mcp/server.py``.
"""
