"""Stage 5 (terminal-for-links): schedule discovered links to the crawl frontier.

Acquires the target (locks while in SCHEDULING) and, in one transaction, writes
one frontier outbox event per pending discovered link (deduped per link), marks
those links scheduled, and then sets the target's status. Because the frontier
events live in the same committed transaction as that status change, downstream
work is durable/recoverable before this stage is considered done.

This stage no longer sets the target to PROCESSED directly — that would mean
"processed" as soon as embed batches were merely *scheduled*, not actually
embedded, which is the bug this design fixes. Instead:

* If the target's document has zero chunks, or every chunk is already
  embedded (``embed_chunks`` may have raced ahead and finished first), the
  target is finalized to PROCESSED here, since no embed batch will ever be
  (or remains to be) scheduled for it.
* Otherwise the target moves to EMBEDDING, an intermediate "waiting on
  embeds" status; only ``embed_chunks`` — once the document's last chunk is
  embedded — moves it on to PROCESSED
  (``UnitOfWork.finalize_target_if_all_chunks_embedded``).

This is also one of the two triggers for ``track_pipeline_status`` (the other
is ``embed_chunks``): poking it here is a no-op unless this call also finalized
the target to PROCESSED (EMBEDDING is still "active" — see
``crawl_target_repo._EMBEDDING_TERMINAL_STATUSES``) — but it's harmless to poke
unconditionally, and it does matter for the zero-chunk-target path above,
which is otherwise never revisited. Embeddings for earlier targets may still
be in flight when this target's link event fires, or may have already
finished before it — either order is fine because the tracker re-derives
completion from the DB rather than trusting message order.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from backend.shared.clients.queue.logging_middleware import log_message_skipped
from backend.shared.clients.queue.pipeline_payloads import (
    ScheduleDiscoveredLinksPayload,
    TrackPipelineStatusPayload,
)
from backend.shared.clients.queue.queue_names import (
    CRAWL_FRONTIER_MANAGER_ACTOR,
    CRAWL_FRONTIER_MANAGER_QUEUE,
    SCHEDULE_DISCOVERED_LINKS_ACTOR,
    SCHEDULE_DISCOVERED_LINKS_QUEUE,
    TRACK_PIPELINE_STATUS_ACTOR,
    TRACK_PIPELINE_STATUS_QUEUE,
)
from backend.shared.models import (
    CrawlTargetStatus,
    OutboxEvent,
    ScheduleDiscoveredLinksSettings,
)
from backend.shared.pipeline.actor_config import load_actor_configs
from backend.shared.storage.sql.sql_store import SqlStore


def schedule_discovered_links(
    *,
    crawl_target_id: str,
    pipeline_id: Optional[str] = None,
    store: SqlStore,
) -> None:
    payload = ScheduleDiscoveredLinksPayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, pipeline_id=pipeline_id
    )
    target_id: UUID = payload.crawl_target_id

    # Lock while in SCHEDULING without changing the status yet; PROCESSED is set
    # inside the transaction below, after the frontier events are written.
    target = store.crawl_targets.acquire(
        target_id=target_id,
        from_statuses=[CrawlTargetStatus.SCHEDULING],
        to_status=CrawlTargetStatus.SCHEDULING,
    )
    if target is None:
        log_message_skipped(
            actor_name=SCHEDULE_DISCOVERED_LINKS_ACTOR,
            queue_name=SCHEDULE_DISCOVERED_LINKS_QUEUE,
            reason="not_in_processable_state",
            extra={"crawl_target_id": str(target_id)},
        )
        return

    # follow_child_links gates whether discovered links are scheduled back to
    # the frontier at all; when off, the target is still finalized (PROCESSED)
    # below, just with no outgoing links.
    cfg = load_actor_configs(store, payload.pipeline_id)
    settings = cfg.schedule_discovered_links if cfg else ScheduleDiscoveredLinksSettings()

    document = store.documents.get_by_crawl_target(target_id)
    pending = (
        store.discovered_links.list_pending_by_document(document.id)
        if document is not None and settings.follow_child_links
        else []
    )

    with store.unit_of_work() as uow:
        scheduled_ids = []
        for link in pending:
            frontier_payload = {
                "url": link.raw_url,
                "parent_document_id": str(link.source_document_id),
                "parent_chunk_id": str(link.source_chunk_id),
                "pipeline_id": payload.pipeline_id,
            }
            uow.add_outbox(
                OutboxEvent(
                    queue_name=CRAWL_FRONTIER_MANAGER_QUEUE,
                    actor_name=CRAWL_FRONTIER_MANAGER_ACTOR,
                    payload=frontier_payload,
                    dedup_key=f"frontier:{link.id}",
                )
            )
            scheduled_ids.append(link.id)

        uow.mark_links_scheduled(scheduled_ids)

        # A target with no document, or whose document has zero chunks
        # (filtered/skipped content), has no embed batches coming — finalize
        # it now, since embed_chunks will never run for it. Same finalization
        # if every chunk already reports embedded (embed_chunks raced ahead).
        # Otherwise wait: move to EMBEDDING and let embed_chunks finalize once
        # the document's last chunk is embedded.
        if document is not None and not uow.document_all_chunks_embedded(document.id):
            uow.set_status(target_id, CrawlTargetStatus.EMBEDDING)
        else:
            uow.set_status(target_id, CrawlTargetStatus.PROCESSED)

        if payload.pipeline_id is not None:
            track_payload = TrackPipelineStatusPayload(
                pipeline_id=UUID(payload.pipeline_id)
            )
            uow.add_outbox(
                OutboxEvent(
                    queue_name=TRACK_PIPELINE_STATUS_QUEUE,
                    actor_name=TRACK_PIPELINE_STATUS_ACTOR,
                    payload=track_payload.to_actor_kwargs(),
                    dedup_key=f"track:{payload.pipeline_id}:links:{target_id}",
                )
            )
