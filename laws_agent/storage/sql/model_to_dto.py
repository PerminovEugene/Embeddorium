from __future__ import annotations

from laws_agent.models import (
    DiscoveredLink,
    DiscoveredLinkStatus,
    Document,
    DocumentChunk,
    OutboxEvent,
    OutboxStatus,
    SourceFetch,
)
from laws_agent.storage.sql.models.discovered_link import DiscoveredLinkORM
from laws_agent.storage.sql.models.document import DocumentORM
from laws_agent.storage.sql.models.chunk import DocumentChunkORM
from laws_agent.storage.sql.models.outbox_event import OutboxEventORM
from laws_agent.storage.sql.models.source_fetch import SourceFetchORM


def _to_document(orm: DocumentORM, include_chunks: bool = False) -> Document:
    return Document(
        id=orm.id,
        source_url=orm.source_url,
        language=orm.language,
        group=orm.group,
        crawl_target_id=orm.crawl_target_id,
        normalized_url=orm.normalized_url,
        final_url=orm.final_url,
        http_status=orm.http_status,
        content_type=orm.content_type,
        content_hash=orm.content_hash,
        text_hash=orm.text_hash,
        parser_version=orm.parser_version,
        chunker_version=orm.chunker_version,
        retrieved_at=orm.retrieved_at,
        text=orm.text,
        created_at=orm.created_at,
        chunks=[_to_chunk(chunk) for chunk in orm.chunks] if include_chunks else [],
    )


def _to_chunk(orm: DocumentChunkORM) -> DocumentChunk:
    return DocumentChunk(
        id=orm.id,
        document_id=orm.document_id,
        text=orm.text,
        chunk_index=orm.chunk_index,
        created_at=orm.created_at,
    )


def _to_source_fetch(orm: SourceFetchORM) -> SourceFetch:
    return SourceFetch(
        id=orm.id,
        crawl_target_id=orm.crawl_target_id,
        final_url=orm.final_url,
        http_status=orm.http_status,
        content_type=orm.content_type,
        content_hash=orm.content_hash,
        raw_content=orm.raw_content,
        redirect_chain=list(orm.redirect_chain or []),
        fetched_at=orm.fetched_at,
    )


def _to_discovered_link(orm: DiscoveredLinkORM) -> DiscoveredLink:
    return DiscoveredLink(
        id=orm.id,
        source_document_id=orm.source_document_id,
        source_chunk_id=orm.source_chunk_id,
        raw_url=orm.raw_url,
        normalized_url=orm.normalized_url,
        anchor_text=orm.anchor_text,
        context_text=orm.context_text,
        group=orm.group,
        status=DiscoveredLinkStatus(orm.status),
        created_at=orm.created_at,
    )


def _to_outbox_event(orm: OutboxEventORM) -> OutboxEvent:
    return OutboxEvent(
        id=orm.id,
        queue_name=orm.queue_name,
        actor_name=orm.actor_name,
        payload=dict(orm.payload or {}),
        dedup_key=orm.dedup_key,
        status=OutboxStatus(orm.status),
        attempts=orm.attempts,
        created_at=orm.created_at,
        sent_at=orm.sent_at,
    )
