import logging
import time
from typing import Any

from dramatiq.middleware import Middleware

logger = logging.getLogger("laws_agent.dramatiq")


class MessageLoggingMiddleware(Middleware):
    def before_enqueue(self, broker, message, delay):
        logger.info(
            "message_enqueue actor=%s queue=%s message_id=%s delay=%s args=%s kwargs=%s",
            message.actor_name,
            message.queue_name,
            message.message_id,
            delay,
            message.args,
            message.kwargs,
        )

    def before_process_message(self, broker, message):
        message.options["started_at"] = time.monotonic()
        logger.info(
            "message_started actor=%s queue=%s message_id=%s args=%s kwargs=%s",
            message.actor_name,
            message.queue_name,
            message.message_id,
            message.args,
            message.kwargs,
        )

    def after_process_message(self, broker, message, *, result=None, exception=None):
        started_at = message.options.get("started_at")
        duration_ms = (
            round((time.monotonic() - started_at) * 1000, 2)
            if started_at is not None
            else None
        )

        if exception is None:
            logger.info(
                "message_finished actor=%s queue=%s message_id=%s duration_ms=%s",
                message.actor_name,
                message.queue_name,
                message.message_id,
                duration_ms,
            )
        else:
            logger.exception(
                "message_failed actor=%s queue=%s message_id=%s duration_ms=%s exception=%s",
                message.actor_name,
                message.queue_name,
                message.message_id,
                duration_ms,
                repr(exception),
            )

    def after_skip_message(self, broker, message):
        started_at = message.options.get("started_at")
        duration_ms = (
            round((time.monotonic() - started_at) * 1000, 2)
            if started_at is not None
            else None
        )
        logger.info(
            "message_skipped actor=%s queue=%s message_id=%s duration_ms=%s",
            message.actor_name,
            message.queue_name,
            message.message_id,
            duration_ms,
        )


def log_message_skipped(
    *,
    actor_name: str,
    reason: str,
    queue_name: str | None = None,
    message_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    logger.info(
        "message_skipped actor=%s queue=%s message_id=%s reason=%s extra=%s",
        actor_name,
        queue_name,
        message_id,
        reason,
        extra or {},
    )
