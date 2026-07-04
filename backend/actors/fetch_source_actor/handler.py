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

from backend.shared.clients.http.failures import FetchFailure
from backend.shared.clients.http.fetcher import HttpFetcher
from backend.shared.clients.http.tls_policy import allow_insecure_tls
from backend.shared.clients.queue.logging_middleware import log_message_skipped
from backend.shared.clients.queue.pipeline_payloads import ParseSourcePayload
from backend.shared.clients.queue.process_web_source_payload import ProcessWebSourcePayload
from backend.shared.clients.queue.queue_names import (
    FETCH_SOURCE_ACTOR,
    FETCH_SOURCE_QUEUE,
    PARSE_SOURCE_ACTOR,
    PARSE_SOURCE_QUEUE,
)
from backend.shared.models import (
    CrawlTargetStatus,
    FetchSourceSettings,
    OutboxEvent,
    SourceFetch,
)
from backend.shared.parsers.registry import is_supported, normalize_content_type
from backend.shared.pipeline.actor_config import load_actor_configs
from backend.shared.pipeline.hashing import sha256_hex
from backend.shared.pipeline.source_files import (
    extension_for_content_type,
    write_source_file,
)
from backend.shared.storage.sql.sql_store import SqlStore


def _content_type_allowed(content_type: str | None, allowlist: str) -> bool:
    """Return whether *content_type* passes an optional comma-separated allowlist.

    An empty allowlist means "no extra restriction" (the parser registry alone
    decides). Otherwise the normalized type must appear in the list.
    """
    allowed = {normalize_content_type(ct) for ct in allowlist.split(",") if ct.strip()}
    if not allowed:
        return True
    return normalize_content_type(content_type) in allowed


def fetch_source(
    *,
    crawl_target_id: str,
    pipeline_id: str | None = None,
    store: SqlStore,
    fetcher: HttpFetcher,
    insecure_tls_policy: Callable[[str], bool] = allow_insecure_tls,
) -> None:
    payload = ProcessWebSourcePayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, pipeline_id=pipeline_id
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

    # Fetch knobs from this run's actor config (TLS, read timeout, content-type
    # allowlist). verify_tls=False opts into insecure TLS in addition to the
    # domain allowlist policy.
    cfg = load_actor_configs(store, payload.pipeline_id)
    settings = cfg.fetch_source if cfg else FetchSourceSettings()
    allow_insecure = (not settings.verify_tls) or insecure_tls_policy(
        target.original_url
    )

    try:
        result = fetcher.fetch(
            target.original_url,
            allow_insecure_tls=allow_insecure,
            read_timeout=settings.timeout_seconds,
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

    if not is_supported(result.content_type) or not _content_type_allowed(
        result.content_type, settings.allowed_content_types
    ):
        store.crawl_targets.update_status(
            target_id=target_id,
            status=CrawlTargetStatus.SKIPPED_UNSUPPORTED,
            skip_reason=f"content_type={result.content_type}",
        )
        return

    raw_path = write_source_file(
        pipeline_id=payload.pipeline_id,
        source_id=str(target_id),
        kind="raw",
        content=result.content,
        extension=extension_for_content_type(result.content_type),
    )
    fetch = SourceFetch(
        crawl_target_id=target_id,
        final_url=result.final_url,
        http_status=result.status_code,
        content_type=result.content_type,
        content_hash=sha256_hex(result.content),
        raw_content_path=raw_path,
        redirect_chain=result.redirect_chain,
    )

    parse_payload = ParseSourcePayload(
        crawl_target_id=target_id,
        pipeline_id=payload.pipeline_id,
    )

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
