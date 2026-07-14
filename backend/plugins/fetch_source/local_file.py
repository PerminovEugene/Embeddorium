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

from backend.plugins.fetch_source.base import (
    FetchContext,
    FetchedSource,
    FetchStrategyConfig,
    SourceFetchError,
    SourceFetchStrategy,
)
from backend.shared.models import CrawlTarget


class LocalFileSourceFetch(SourceFetchStrategy):
    config = FetchStrategyConfig(
        name="local",
        label="Local file read",
        description=(
            "Reads the target's local XML file from disk and routes the raw "
            "content to filter_documents."
        ),
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

    # next_outbox_event is inherited from SourceFetchStrategy — routes to
    # filter_documents, identical to the web strategy.
