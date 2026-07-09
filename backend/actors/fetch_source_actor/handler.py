"""Stage 1: fetch a crawl target's raw content and persist the fetch result.

Merged actor serving both ingestion chains. Acquires the target
(QUEUED/FAILED_TRANSIENT → FETCHING), selects a fetch strategy plugin
(``backend/plugins/fetch_source``) by the run's dataset ``source_type`` —
web targets are fetched over HTTP(S), local-file targets are read from disk —
then, in one transaction, stores the ``SourceFetch`` provenance row, advances
to FETCHED and writes the outbox event for the strategy's next stage
(``parse_source`` for web, ``filter_documents`` for local files). Messages
without a resolvable run config fall back to inferring the source type from
the target's normalized URL.
"""

from __future__ import annotations

from typing import Callable
from uuid import UUID

from backend.plugins.fetch_source.base import (
    FetchContext,
    SourceFetchError,
    UnsupportedSourceError,
)
from backend.plugins.fetch_source.registry import build_fetch_strategy
from backend.shared.clients.http.fetcher import HttpFetcher
from backend.shared.clients.http.tls_policy import allow_insecure_tls
from backend.shared.clients.queue.fetch_source_payload import FetchSourcePayload
from backend.shared.clients.queue.logging_middleware import log_message_skipped
from backend.shared.clients.queue.queue_names import (
    FETCH_SOURCE_ACTOR,
    FETCH_SOURCE_QUEUE,
)
from backend.shared.models import (
    CrawlTargetStatus,
    FetchSourceSettings,
    SourceFetch,
)
from backend.shared.pipeline.actor_config import (
    load_actor_configs,
    load_dataset_source_type,
)
from backend.shared.pipeline.hashing import sha256_hex
from backend.shared.pipeline.source_files import write_source_file
from backend.shared.storage.sql.sql_store import SqlStore


def _infer_source_type(normalized_url: str) -> str:
    """Fallback for messages without run config: the validate_source local
    strategy always writes ``file://`` normalized URLs, so that prefix alone
    identifies a local-file target."""
    return "local" if normalized_url.startswith("file://") else "web"


def fetch_source(
    *,
    crawl_target_id: str,
    pipeline_id: str | None = None,
    store: SqlStore,
    fetcher: HttpFetcher,
    insecure_tls_policy: Callable[[str], bool] = allow_insecure_tls,
) -> None:
    payload = FetchSourcePayload.from_actor_kwargs(
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
    # allowlist — all consumed by the web strategy).
    cfg = load_actor_configs(store, payload.pipeline_id)
    settings = cfg.fetch_source if cfg else FetchSourceSettings()

    source_type = load_dataset_source_type(
        store, payload.pipeline_id
    ) or _infer_source_type(target.normalized_url)
    strategy = build_fetch_strategy(source_type)

    ctx = FetchContext(
        settings=settings,
        pipeline_id=payload.pipeline_id,
        fetcher=fetcher,
        insecure_tls_policy=insecure_tls_policy,
    )

    try:
        fetched = strategy.fetch(target=target, ctx=ctx)
    except UnsupportedSourceError as exc:
        store.crawl_targets.update_status(
            target_id=target_id,
            status=CrawlTargetStatus.SKIPPED_UNSUPPORTED,
            skip_reason=exc.skip_reason,
        )
        return
    except SourceFetchError as exc:
        if exc.transient:
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

    raw_path = write_source_file(
        pipeline_id=payload.pipeline_id,
        source_id=str(target_id),
        kind="raw",
        content=fetched.content,
        extension=fetched.extension,
    )
    fetch = SourceFetch(
        crawl_target_id=target_id,
        final_url=fetched.final_url,
        http_status=fetched.http_status,
        content_type=fetched.content_type,
        content_hash=sha256_hex(fetched.content),
        raw_content_path=raw_path,
        redirect_chain=fetched.redirect_chain,
    )

    with store.unit_of_work() as uow:
        uow.upsert_source_fetch(fetch)
        uow.set_status(target_id, CrawlTargetStatus.FETCHED)
        uow.add_outbox(
            strategy.next_outbox_event(
                target_id=target_id, pipeline_id=payload.pipeline_id
            )
        )
