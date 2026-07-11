"""Local-file fetch strategy: disk read, routing onward to ``filter_documents``.

Carries over the read half of the old fetch_file_source actor: the target's
``original_url`` is an absolute path (resolved by the validate_source local
strategy); read it as UTF-8 XML and record a synthetic ``http_status=0``
fetch. A read failure is permanent — validate_source already checked
existence/readability, so a file that vanished afterwards will not come back
on retry.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from backend.plugins._fields import FieldSpec
from backend.plugins.fetch_source.base import (
    FetchContext,
    FetchedSource,
    FetchStrategyConfig,
    SourceFetchError,
    SourceFetchStrategy,
)
from backend.shared.clients.queue.pipeline_payloads import FilterDocumentsPayload
from backend.shared.clients.queue.queue_names import (
    FILTER_DOCUMENTS_ACTOR,
    FILTER_DOCUMENTS_QUEUE,
)
from backend.shared.models import CrawlTarget, OutboxEvent


class LocalFileSourceFetch(SourceFetchStrategy):
    config = FetchStrategyConfig(
        name="local",
        label="Local file read",
        description=(
            "Reads the target's local XML file from disk and routes the raw "
            "content to filter_documents."
        ),
        # file_glob is this strategy's knob (FetchSourceSettings.file_glob).
        # It is applied at seed time when a folder seed enumerates its files,
        # not inside the actor, but it is declared here so the UI renders it on
        # the local strategy's settings form.
        fields=[
            FieldSpec(
                key="file_glob",
                label="File glob",
                type="text",
                default="*.xml",
                placeholder="*.xml",
            ),
        ],
    )

    def fetch(self, *, target: CrawlTarget, ctx: FetchContext) -> FetchedSource:
        try:
            content = Path(target.original_url).read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError as exc:
            raise SourceFetchError(str(exc), transient=False) from exc

        return FetchedSource(
            content=content,
            content_type="application/xml",
            final_url=target.normalized_url,
            http_status=0,
            redirect_chain=[],
            extension="xml",
        )

    def next_outbox_event(
        self, *, target_id: UUID, pipeline_id: str | None
    ) -> OutboxEvent:
        payload = FilterDocumentsPayload(
            crawl_target_id=target_id, pipeline_id=pipeline_id
        )
        return OutboxEvent(
            queue_name=FILTER_DOCUMENTS_QUEUE,
            actor_name=FILTER_DOCUMENTS_ACTOR,
            payload=payload.to_actor_kwargs(),
            dedup_key=f"filter:{target_id}",
        )
