from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, Field


class OutboxStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"


class OutboxEvent(BaseModel):
    """A queue message persisted in the same transaction as the domain change
    that produced it. The outbox dispatcher publishes pending events to RabbitMQ.

    ``dedup_key`` is globally unique, so writing the same logical event twice
    (e.g. on a worker retry) is a no-op instead of a duplicate enqueue.
    """

    id: Optional[uuid.UUID] = None
    queue_name: str
    actor_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    dedup_key: str
    status: OutboxStatus = OutboxStatus.PENDING
    attempts: int = 0
    created_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
