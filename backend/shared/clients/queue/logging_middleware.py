import logging
import time
import uuid
from typing import Any, Dict, Optional

from dramatiq.middleware import Middleware

from backend.shared.log_routing import register_pipeline_name

logger = logging.getLogger("backend.dramatiq")


class MessageLoggingMiddleware(Middleware):
    """Structured message logging plus run-folder naming.

    Beyond emitting enqueue/start/finish records, this middleware resolves each
    message's ``pipeline_id`` to its run name and registers the on-disk folder
    name (``<pipeline_id>__<name>``) via
    :func:`backend.shared.log_routing.register_pipeline_name`, so this worker's
    logs and source files land in a human-identifiable folder instead of a bare
    UUID. Resolution hits the DB once per ``pipeline_id`` per process (cached in
    ``_resolved``) and never blocks message processing: any failure is logged
    and the run keeps its bare-UUID folder.
    """

    def __init__(self) -> None:
        # pipeline_ids already resolved (or attempted) this process, so the run
        # row is queried at most once per pipeline regardless of message volume.
        self._resolved: set[str] = set()
        # Lazily created on first use so importing this module (e.g. from the
        # server, which never consumes) doesn't open a DB pool.
        self._store = None

    def _register_run_folder(self, message) -> None:
        pipeline_id = message.kwargs.get("pipeline_id")
        if not pipeline_id or pipeline_id in self._resolved:
            return
        self._resolved.add(pipeline_id)
        try:
            name = self._run_name(pipeline_id)
        except Exception as exc:  # never let logging setup break processing
            logger.warning(
                "pipeline_name_resolve_failed pipeline_id=%s exception=%s",
                pipeline_id,
                repr(exc),
            )
            name = None
        register_pipeline_name(pipeline_id, name)

    def _run_name(self, pipeline_id: str) -> Optional[str]:
        run = self._get_store().pipeline_runs.get(uuid.UUID(pipeline_id))
        return run.name if run is not None else None

    def _get_store(self):
        if self._store is None:
            # Imported here (not at module scope) to keep the queue client's
            # import of this middleware free of the whole storage layer.
            from backend.shared.storage.sql.core.engine import SqlPoolConfig
            from backend.shared.storage.sql.sql_store import SqlStore

            self._store = SqlStore(
                pool_config=SqlPoolConfig(pool_size=1, max_overflow=1),
                application_name="message_logging_middleware",
            )
        return self._store

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
        # Runs before the actor body (and its log_to(...) context), so the run
        # folder name is registered before any run-scoped file is written.
        self._register_run_folder(message)
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
    queue_name: Optional[str] = None,
    message_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    logger.info(
        "message_skipped actor=%s queue=%s message_id=%s reason=%s extra=%s",
        actor_name,
        queue_name,
        message_id,
        reason,
        extra or {},
    )
