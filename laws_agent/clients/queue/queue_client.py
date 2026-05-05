# laws_agent/queues/queue_client.py

import pika
from dramatiq.brokers.rabbitmq import RabbitmqBroker

from laws_agent import config
from laws_agent.clients.queue.logging_middleware import MessageLoggingMiddleware


class QueueClient:
    def __init__(self) -> None:
        self._broker: RabbitmqBroker | None = None

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
                    "client_properties": {"connection_name": connection_name},
                }]
            )
            self._broker.add_middleware(MessageLoggingMiddleware())

        return self._broker
