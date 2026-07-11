"""Shared FastAPI dependencies for the matcher API.

The whole server process shares one instance of each backing client — a
``SqlStore`` (SQLAlchemy engine + pool), a ``QdrantClient`` (HTTP pool), and a
Dramatiq RabbitMQ broker — all built once in ``main.py``'s lifespan and stashed
on ``app.state``. Handlers reach them through ``Depends(...)`` rather than
constructing their own: a per-request client would spin up a fresh pool/
connection and tear it down again, defeating the pooling these clients are
designed for.
"""

from __future__ import annotations

from dramatiq.brokers.rabbitmq import RabbitmqBroker
from fastapi import Request
from qdrant_client import QdrantClient

from backend.shared.storage.sql.sql_store import SqlStore


def get_sql_store(request: Request) -> SqlStore:
    """Return the process-wide ``SqlStore`` shared by every request."""
    return request.app.state.sql_store


def get_qdrant_client(request: Request) -> QdrantClient:
    """Return the process-wide Qdrant client shared by every request.

    Callers wrap it in a ``VectorStore(collection, client=...)`` because the
    collection is per-request while the client (and its connection pool) is not.
    """
    return request.app.state.qdrant_client


def get_broker(request: Request) -> RabbitmqBroker:
    """Return the process-wide Dramatiq RabbitMQ broker shared by every request."""
    return request.app.state.broker
