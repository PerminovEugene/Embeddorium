# backend/shared/clients/queue/queue_client.py

from typing import Optional

import pika
from dramatiq.brokers.rabbitmq import RabbitmqBroker

from backend.shared import config
from backend.shared.clients.queue.logging_middleware import MessageLoggingMiddleware


class QueueClient:
    def __init__(self) -> None:
        self._broker: Optional[RabbitmqBroker] = None

    def create(self, connection_name: str) -> RabbitmqBroker:
        if self._broker is None:
            # params = 
            # print(params, config.RABBITMQ_USER, config.RABBITMQ_PASSWORD)
            self._broker = RabbitmqBroker(
                parameters=[{
                    "host": config.RABBITMQ_HOST,
                    "port": int(config.RABBITMQ_PORT),
                    "virtual_host": config.RABBITMQ_VHOST,
                    "credentials": pika.PlainCredentials(
                        config.RABBITMQ_USER, config.RABBITMQ_PASSWORD
                    ),
                    # Negotiated heartbeat is min(this, server's suggested value),
                    # so this only takes effect alongside `heartbeat` in
                    # rabbitmq/rabbitmq.conf. Kept generous (10 min) so brief
                    # Docker Desktop VM stalls don't trip "missed heartbeats" and
                    # churn every worker connection. See rabbitmq.conf for context.
                    "heartbeat": 600,
                    "client_properties": {"connection_name": connection_name},
                }]
            )
            self._broker.add_middleware(MessageLoggingMiddleware())

        return self._broker
