"""Cross-cutting: detect that a pipeline run has no more work and complete it.

Unlike the numbered crawl-chain stages, this actor is not part of a linear
pipeline of its own — it is a listener triggered from the *tail* of the
ingestion chain, currently by two different producers:

* ``embed_chunks`` — fires every time an embed batch finishes. This is now
  also the actor that finalizes a target to ``processed`` (once every chunk
  of its document is embedded), so most runs' completion is ultimately driven
  from here.
* ``schedule_discovered_links`` — fires every time a crawl target finishes
  link-scheduling, whether that leaves it at the intermediate ``embedding``
  status (waiting on ``embed_chunks`` to finalize it) or, for a
  zero-chunk/no-document target, finalizes it to ``processed`` directly since
  no embed batch will ever be scheduled for it.

Both triggers are needed because embedding is asynchronous relative to crawl
target status: the last embed for a run can finish either before or after its
owning target reaches ``processed``. Relying on only one of the two would
leave a race where the run never gets marked complete (e.g. all embeds finish
first, but the tracker is never poked again once the target is later marked
processed; or the target is processed first, but the tracker isn't re-invoked
once the trailing embeds land). Firing from both, and always re-deriving the
completion condition from the database rather than trusting message order or
payload state, closes that race regardless of which side finishes last.

``count_active_for_pipeline`` (see ``crawl_target_repo``) is what keeps this
correct with the ``embedding`` intermediate status: a target sitting in
``embedding`` is deliberately *not* in ``_EMBEDDING_TERMINAL_STATUSES``, so it
still counts as active and blocks completion until ``embed_chunks``
transitions it to ``processed`` — condition 1 below only becomes true once
every target has actually finished embedding, not merely scheduled it.

Pure logic — no broker/dramatiq concerns, matching the other actor handlers.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from backend.shared.clients.queue.logging_middleware import log_message_skipped
from backend.shared.clients.queue.pipeline_payloads import TrackPipelineStatusPayload
from backend.shared.clients.queue.queue_names import (
    TRACK_PIPELINE_STATUS_ACTOR,
    TRACK_PIPELINE_STATUS_QUEUE,
)
from backend.shared.storage.sql.sql_store import SqlStore

logger = logging.getLogger(__name__)


def track_pipeline_status(
    *,
    pipeline_id: str,
    store: SqlStore,
) -> None:
    """Complete *pipeline_id* if, and only if, no more work is coming.

    A run is complete when both hold:

    1. ``crawl_targets.count_active_for_pipeline(pipeline_id) == 0`` — every
       target has reached one of ``_EMBEDDING_TERMINAL_STATUSES``: either it
       will never produce another embed batch (skipped/failed), or it already
       reached ``processed`` (which itself requires every one of its chunks
       to be embedded). A target sitting in ``embedding`` — scheduled but not
       yet fully embedded — is deliberately excluded from that set, so it
       still counts as active here.
    2. ``embeddings_completed >= embeddings_scheduled`` — every batch that was
       ever scheduled has also finished.

    Every early return here is a deliberate no-op, not an error: this actor
    is invoked far more often than a run actually completes (once per embed
    batch and once per processed target), so most invocations correctly find
    "not done yet" and return. The tracker re-reads everything it needs from
    the DB by ``pipeline_id`` alone.
    """
    try:
        run_id = uuid.UUID(pipeline_id)
    except (ValueError, TypeError):
        log_message_skipped(
            actor_name=TRACK_PIPELINE_STATUS_ACTOR,
            queue_name=TRACK_PIPELINE_STATUS_QUEUE,
            reason="invalid_pipeline_id",
            extra={"pipeline_id": pipeline_id},
        )
        return

    # Payload round-trip is a no-op today (there is nothing left to parse
    # beyond pipeline_id), but going through it keeps this handler consistent
    # with every other stage and gives future fields a natural home.
    TrackPipelineStatusPayload.from_actor_kwargs(pipeline_id=pipeline_id)

    run = store.pipeline_runs.get(run_id)
    if run is None or run.status != "running":
        # Already completed/failed, still pending, or unknown — nothing to do.
        # This is the common steady-state outcome once a run has completed:
        # later, redelivered or duplicate triggers land here and exit quietly.
        log_message_skipped(
            actor_name=TRACK_PIPELINE_STATUS_ACTOR,
            queue_name=TRACK_PIPELINE_STATUS_QUEUE,
            reason="run_not_running",
            extra={
                "pipeline_id": pipeline_id,
                "status": run.status if run is not None else None,
            },
        )
        return

    if store.crawl_targets.count_active_for_pipeline(run_id) > 0:
        # More targets may still schedule embed batches.
        return

    if run.embeddings_completed < run.embeddings_scheduled:
        # Every target is done, but embeds triggered by the last few targets
        # haven't all finished yet.
        return

    completed = store.pipeline_runs.complete_if_running(
        run_id, finished_at=datetime.now(tz=timezone.utc)
    )
    if completed is not None:
        logger.info(
            "pipeline_run_completed pipeline_id=%s embeddings_scheduled=%s "
            "embeddings_completed=%s",
            pipeline_id,
            run.embeddings_scheduled,
            run.embeddings_completed,
        )
