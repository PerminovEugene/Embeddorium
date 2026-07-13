"""The fetch_source strategy plugin interface.

A fetch strategy owns the source-type-specific half of the ``fetch_source``
actor: acquiring the raw content (HTTP fetch vs local file read). Everything
shared between source types — target acquisition/locking, status transitions,
writing the raw source file, persisting the ``SourceFetch`` row and committing
the outbox event — stays in the actor, so a strategy is a near-pure function
``CrawlTarget -> FetchedSource``.

Both built-in strategies (web and local) route onward to the same next stage,
``filter_documents``, so the routing decision is a shared concrete default on
:class:`SourceFetchStrategy` rather than a per-strategy override. The filter
stage then advances relevant documents to ``parse_source`` (both chains become
fetch → filter → parse).

Failure contract: a strategy raises :class:`UnsupportedSourceError` for
content the pipeline should skip permanently (SKIPPED_UNSUPPORTED) and
:class:`SourceFetchError` for fetch failures; ``transient=True`` failures are
re-raised by the actor so Dramatiq retries with backoff, ``transient=False``
ones mark the target FAILED_PERMANENT.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, ClassVar
from uuid import UUID

from backend.plugins._fields import FieldSpec
from backend.shared.clients.queue.pipeline_payloads import FilterDocumentsPayload
from backend.shared.clients.queue.queue_names import (
    FILTER_DOCUMENTS_ACTOR,
    FILTER_DOCUMENTS_QUEUE,
)
from backend.shared.models import CrawlTarget, FetchSourceSettings, OutboxEvent

if TYPE_CHECKING:
    from backend.shared.clients.http.fetcher import HttpFetcher


@dataclass(frozen=True)
class FetchStrategyConfig:
    """Static description of a fetch strategy plugin.

    ``name`` is the dataset ``source_type`` the strategy serves ("web" /
    "local") and the key it is looked up under in the registry. ``fields``
    describes the per-strategy knobs the actor reads out of
    :class:`~backend.shared.models.pipeline_run.FetchSourceSettings`, so the UI
    can render this strategy's settings form (served camelCased like every
    other plugin config).
    """

    name: str
    label: str
    description: str
    fields: list[FieldSpec] = field(default_factory=list)


@dataclass(frozen=True)
class FetchContext:
    """Dependencies and per-run knobs handed to a strategy's ``fetch``.

    ``fetcher``/``insecure_tls_policy`` are only used by the web strategy;
    the local strategy reads straight from disk.
    """

    settings: FetchSourceSettings
    pipeline_id: str | None = None
    fetcher: "HttpFetcher | None" = None
    insecure_tls_policy: Callable[[str], bool] | None = None


@dataclass(frozen=True)
class FetchedSource:
    """The raw content of one successfully fetched source.

    ``extension`` is the file extension the actor writes the raw artefact
    under (e.g. ``"html"``/``"xml"``).
    """

    content: str
    content_type: str | None
    final_url: str
    http_status: int
    redirect_chain: list[str]
    extension: str


class SourceFetchError(Exception):
    """A fetch failed; ``transient`` selects retry vs permanent failure."""

    def __init__(self, message: str, *, transient: bool) -> None:
        super().__init__(message)
        self.transient = transient


class UnsupportedSourceError(Exception):
    """The source's content is unsupported; skip it permanently."""

    def __init__(self, skip_reason: str) -> None:
        super().__init__(skip_reason)
        self.skip_reason = skip_reason


class SourceFetchStrategy(ABC):
    """Base class every fetch_source strategy plugin subclasses."""

    config: ClassVar[FetchStrategyConfig]

    @abstractmethod
    def fetch(self, *, target: CrawlTarget, ctx: FetchContext) -> FetchedSource:
        """Acquire *target*'s raw content, or raise the typed failures above."""
        raise NotImplementedError

    def next_outbox_event(
        self, *, target_id: UUID, pipeline_id: str | None
    ) -> OutboxEvent:
        """Build the outbox event that triggers this chain's next stage.

        Every source type routes onward to ``filter_documents`` (which then
        advances relevant documents to ``parse_source``). This is a concrete
        default because the routing is identical for web and local sources;
        a future strategy that needs different routing can override it.
        """
        payload = FilterDocumentsPayload(
            crawl_target_id=target_id, pipeline_id=pipeline_id
        )
        return OutboxEvent(
            queue_name=FILTER_DOCUMENTS_QUEUE,
            actor_name=FILTER_DOCUMENTS_ACTOR,
            payload=payload.to_actor_kwargs(),
            dedup_key=f"filter:{target_id}",
        )
