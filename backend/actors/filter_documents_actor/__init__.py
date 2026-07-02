"""filter_documents actor package (local file chain relevance gate)."""

from backend.actors.filter_documents_actor.handler import filter_documents
from backend.actors.filter_documents_actor.launcher import (
    filter_documents as filter_documents_actor,
    rabbitmq_broker,
    sql_store,
)

__all__ = [
    "filter_documents",
    "filter_documents_actor",
    "rabbitmq_broker",
    "sql_store",
]
