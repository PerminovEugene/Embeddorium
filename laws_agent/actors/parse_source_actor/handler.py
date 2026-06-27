"""Stage 2: parse a fetched source into normalized text + a Document.

Acquires the target (FETCHED/FILTERED → PARSING; the latter is how the
local-file XML chain re-joins this stage after ``filter_tax_acts``), loads
the persisted ``SourceFetch``, selects a parser by content type, and in one
transaction stores the Document (with provenance + ``text_hash``), advances
to PARSED and writes the outbox event that triggers ``chunk_document``.
"""

from __future__ import annotations

from uuid import UUID

from laws_agent.clients.queue.logging_middleware import log_message_skipped
from laws_agent.clients.queue.pipeline_payloads import (
    ChunkDocumentPayload,
    ParseSourcePayload,
)
from laws_agent.clients.queue.queue_names import (
    CHUNK_DOCUMENT_ACTOR,
    CHUNK_DOCUMENT_QUEUE,
    PARSE_SOURCE_ACTOR,
    PARSE_SOURCE_QUEUE,
)
from laws_agent.models import CrawlTargetStatus, Document, OutboxEvent
from laws_agent.parsers.registry import PARSER_VERSION, get_parser
from laws_agent.parsers.text_splitter import CHUNKER_VERSION
from laws_agent.pipeline.hashing import sha256_hex
from laws_agent.storage.sql.sql_store import SqlStore


def parse_source(*, crawl_target_id: str, group: str, store: SqlStore) -> None:
    payload = ParseSourcePayload.from_actor_kwargs(
        crawl_target_id=crawl_target_id, group=group
    )
    target_id: UUID = payload.crawl_target_id

    target = store.crawl_targets.acquire(
        target_id=target_id,
        from_statuses=[
            CrawlTargetStatus.FETCHED,
            CrawlTargetStatus.PARSING,
            CrawlTargetStatus.FILTERED,
        ],
        to_status=CrawlTargetStatus.PARSING,
    )
    if target is None:
        log_message_skipped(
            actor_name=PARSE_SOURCE_ACTOR,
            queue_name=PARSE_SOURCE_QUEUE,
            reason="not_in_processable_state",
            extra={"crawl_target_id": str(target_id)},
        )
        return

    fetch = store.source_fetches.get_by_crawl_target(target_id)
    if fetch is None:
        # The fetch row should exist; treat its absence as transient (e.g. a
        # not-yet-visible commit) so Dramatiq retries rather than dropping work.
        store.crawl_targets.update_status(
            target_id=target_id,
            status=CrawlTargetStatus.FAILED_TRANSIENT,
            error="source fetch missing",
        )
        raise RuntimeError(f"source fetch missing for target {target_id}")

    parser = get_parser(fetch.content_type)
    if parser is None:
        store.crawl_targets.update_status(
            target_id=target_id,
            status=CrawlTargetStatus.SKIPPED_UNSUPPORTED,
            skip_reason=f"content_type={fetch.content_type}",
        )
        return

    text = parser.parse(fetch.raw_content, fetch.final_url)

    document = Document(
        source_url=target.original_url,
        crawl_target_id=target_id,
        group=payload.group,
        language="unknown",
        normalized_url=target.normalized_url,
        final_url=fetch.final_url,
        http_status=fetch.http_status,
        content_type=fetch.content_type,
        content_hash=fetch.content_hash,
        text_hash=sha256_hex(text),
        parser_version=PARSER_VERSION,
        chunker_version=CHUNKER_VERSION,
        retrieved_at=fetch.fetched_at,
        text=text,
    )

    chunk_payload = ChunkDocumentPayload(crawl_target_id=target_id, group=payload.group)

    with store.unit_of_work() as uow:
        saved = uow.upsert_document(document)
        uow.set_status(target_id, CrawlTargetStatus.PARSED, document_id=saved.id)
        uow.add_outbox(
            OutboxEvent(
                queue_name=CHUNK_DOCUMENT_QUEUE,
                actor_name=CHUNK_DOCUMENT_ACTOR,
                payload=chunk_payload.to_actor_kwargs(),
                dedup_key=f"chunk:{target_id}",
            )
        )
