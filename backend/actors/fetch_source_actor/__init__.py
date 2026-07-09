"""Merged fetch_source actor package (pipeline stage 1 of both chains).

Importable at ``backend.actors.fetch_source_actor`` so Dramatiq can load it
by module path and tests can import the pure ``fetch_source`` handler. The
web-vs-local behavior lives in the strategy plugins under
``backend/plugins/fetch_source``.
"""

from backend.actors.fetch_source_actor.handler import fetch_source
from backend.actors.fetch_source_actor.launcher import (
    fetch_source as fetch_source_actor,
    http_fetcher,
    rabbitmq_broker,
    sql_store,
)

__all__ = [
    "fetch_source",
    "fetch_source_actor",
    "http_fetcher",
    "rabbitmq_broker",
    "sql_store",
]
