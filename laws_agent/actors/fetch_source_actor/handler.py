"""Stage 1: fetch a crawl target's URL and persist the raw fetch result.

Acquires the target (QUEUED/FAILED_TRANSIENT → FETCHING), fetches over TLS
(insecure only for allowlisted domains), classifies failures as transient
(retry) vs permanent (give up), rejects unsupported content types, then in one
transaction stores the ``SourceFetch`` provenance row, advances to FETCHED and
writes the outbox event that triggers ``parse_source``.
"""

from __future__ import annotations

from typing import Callable
from uuid import UUID

from laws_agent.clients.http.failures import FetchFailure
from laws_agent.clients.http.fetcher import HttpFetcher
from laws_agent.clients.http.tls_policy import allow_insecure_tls
from laws_agent.clients.queue.logging_middleware import log_message_skipped
from laws_agent.clients.queue.pipeline_payloads import ParseSourcePayload
from laws_agent.clients.queue.process_web_source_payload import ProcessWebSourcePayload
from laws_agent.clients.queue.queue_names import (
    FETCH_SOURCE_ACTOR,
    FETCH_SOURCE_QUEUE,
    PARSE_SOURCE_ACTOR,
    PARSE_SOURCE_QUEUE,
)
from laws_agent.models import CrawlTargetStatus, OutboxEvent, SourceFetch
from laws_agent.parsers.registry import is_supported
from laws_agent.pipeline.hashing import sha256_hex
from laws_agent.storage.sql.sql_store import SqlStore


def fetch_source(
    *,
    crawl_target_id: str,
    group: str,
    store: SqlStore,
    fetcher: HttpFetcher,
    insecure_tls_policy: Callable[[str], bool] = allow_insecure_tls,
) -> None:
    payload = ProcessWebSourcePayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, group=group
    )
    target_id: UUID = payload.crawl_target_id

    if store.crawl_targets.get(target_id) is None:
        log_message_skipped(
            actor_name=FETCH_SOURCE_ACTOR,
            queue_name=FETCH_SOURCE_QUEUE,
            reason="crawl_target_not_found",
            extra={"crawl_target_id": str(target_id)},
        )
        return

    target = store.crawl_targets.acquire(
        target_id=target_id,
        from_statuses=[
            CrawlTargetStatus.QUEUED,
            CrawlTargetStatus.FAILED_TRANSIENT,
            CrawlTargetStatus.FETCHING,
        ],
        to_status=CrawlTargetStatus.FETCHING,
    )
    if target is None:
        log_message_skipped(
            actor_name=FETCH_SOURCE_ACTOR,
            queue_name=FETCH_SOURCE_QUEUE,
            reason="not_in_processable_state",
            extra={"crawl_target_id": str(target_id)},
        )
        return

    try:
        result = fetcher.fetch(
            target.original_url,
            allow_insecure_tls=insecure_tls_policy(target.original_url),
        )
    except FetchFailure as exc:
        if exc.is_transient:
            store.crawl_targets.update_status(
                target_id=target_id,
                status=CrawlTargetStatus.FAILED_TRANSIENT,
                error=str(exc),
            )
            raise  # let Dramatiq retry with backoff
        store.crawl_targets.update_status(
            target_id=target_id,
            status=CrawlTargetStatus.FAILED_PERMANENT,
            error=str(exc),
        )
        return

    if not is_supported(result.content_type):
        store.crawl_targets.update_status(
            target_id=target_id,
            status=CrawlTargetStatus.SKIPPED_UNSUPPORTED,
            skip_reason=f"content_type={result.content_type}",
        )
        return

    fetch = SourceFetch(
        crawl_target_id=target_id,
        final_url=result.final_url,
        http_status=result.status_code,
        content_type=result.content_type,
        content_hash=sha256_hex(result.content),
        raw_content=result.content,
        redirect_chain=result.redirect_chain,
    )

    parse_payload = ParseSourcePayload(crawl_target_id=target_id, group=payload.group)

    with store.unit_of_work() as uow:
        uow.upsert_source_fetch(fetch)
        uow.set_status(target_id, CrawlTargetStatus.FETCHED)
        uow.add_outbox(
            OutboxEvent(
                queue_name=PARSE_SOURCE_QUEUE,
                actor_name=PARSE_SOURCE_ACTOR,
                payload=parse_payload.to_actor_kwargs(),
                dedup_key=f"parse:{target_id}",
            )
        )
