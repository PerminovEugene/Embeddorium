# laws_agent/queues/queue_client.py

import pika
from dramatiq.brokers.rabbitmq import RabbitmqBroker

from laws_agent import config


class QueueClient:
    def __init__(self) -> None:
        self._broker: RabbitmqBroker | None = None

    def create(self, connection_name: str) -> RabbitmqBroker:
        if self._broker is None:
            self._broker = RabbitmqBroker(
                parameters=[{
                    "host": config.RABBITMQ_HOST,
                    "port": int(config.RABBITMQ_PORT),
                    "virtual_host": config.RABBITMQ_VHOST,
                    "credentials": pika.PlainCredentials(
                        config.RABBITMQ_USER, config.RABBITMQ_PASSWORD
                    ),
                    "client_properties": {"connection_name": connection_name},
                }]
            )

        return self._broker
