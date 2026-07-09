"""Web fetch strategy: HTTP(S) fetch, routing onward to ``parse_source``.

Carries over the old fetch_source actor behavior: fetch over TLS (insecure
only when the run disables verification or the domain is allowlisted),
classify failures as transient (retry) vs permanent (give up), and reject
content types the parser registry (or the run's own allowlist) does not
support.
"""

from __future__ import annotations

from uuid import UUID

from backend.plugins.fetch_source.base import (
    FetchContext,
    FetchedSource,
    FetchStrategyConfig,
    SourceFetchError,
    SourceFetchStrategy,
    UnsupportedSourceError,
)
from backend.shared.clients.http.failures import FetchFailure
from backend.shared.clients.http.tls_policy import allow_insecure_tls
from backend.shared.clients.queue.pipeline_payloads import ParseSourcePayload
from backend.shared.clients.queue.queue_names import (
    PARSE_SOURCE_ACTOR,
    PARSE_SOURCE_QUEUE,
)
from backend.shared.models import CrawlTarget, OutboxEvent
from backend.shared.parsers.registry import is_supported, normalize_content_type
from backend.shared.pipeline.source_files import extension_for_content_type


def _content_type_allowed(content_type: str | None, allowlist: str) -> bool:
    """Return whether *content_type* passes an optional comma-separated allowlist.

    An empty allowlist means "no extra restriction" (the parser registry alone
    decides). Otherwise the normalized type must appear in the list.
    """
    allowed = {normalize_content_type(ct) for ct in allowlist.split(",") if ct.strip()}
    if not allowed:
        return True
    return normalize_content_type(content_type) in allowed


class WebSourceFetch(SourceFetchStrategy):
    config = FetchStrategyConfig(
        name="web",
        label="Web fetch",
        description=(
            "Fetches the target URL over HTTP(S) and routes the raw content "
            "to parse_source."
        ),
    )

    def fetch(self, *, target: CrawlTarget, ctx: FetchContext) -> FetchedSource:
        if ctx.fetcher is None:
            raise SourceFetchError(
                "web fetch strategy requires an HTTP fetcher", transient=False
            )

        # verify_tls=False opts into insecure TLS in addition to the domain
        # allowlist policy.
        insecure_policy = ctx.insecure_tls_policy or allow_insecure_tls
        allow_insecure = (not ctx.settings.verify_tls) or insecure_policy(
            target.original_url
        )

        try:
            result = ctx.fetcher.fetch(
                target.original_url,
                allow_insecure_tls=allow_insecure,
                read_timeout=ctx.settings.timeout_seconds,
            )
        except FetchFailure as exc:
            raise SourceFetchError(str(exc), transient=exc.is_transient) from exc

        if not is_supported(result.content_type) or not _content_type_allowed(
            result.content_type, ctx.settings.allowed_content_types
        ):
            raise UnsupportedSourceError(f"content_type={result.content_type}")

        return FetchedSource(
            content=result.content,
            content_type=result.content_type,
            final_url=result.final_url,
            http_status=result.status_code,
            redirect_chain=result.redirect_chain,
            extension=extension_for_content_type(result.content_type),
        )

    def next_outbox_event(
        self, *, target_id: UUID, pipeline_id: str | None
    ) -> OutboxEvent:
        payload = ParseSourcePayload(crawl_target_id=target_id, pipeline_id=pipeline_id)
        return OutboxEvent(
            queue_name=PARSE_SOURCE_QUEUE,
            actor_name=PARSE_SOURCE_ACTOR,
            payload=payload.to_actor_kwargs(),
            dedup_key=f"parse:{target_id}",
        )
