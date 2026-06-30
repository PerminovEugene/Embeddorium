"""filter_tax_acts actor package (local XML chain tax-relevance gate)."""

from backend.actors.filter_tax_acts_actor.handler import filter_tax_acts
from backend.actors.filter_tax_acts_actor.launcher import (
    filter_tax_acts as filter_tax_acts_actor,
    rabbitmq_broker,
    sql_store,
)

__all__ = [
    "filter_tax_acts",
    "filter_tax_acts_actor",
    "rabbitmq_broker",
    "sql_store",
]
