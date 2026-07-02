from __future__ import annotations

from backend.shared.models import (
    Dataset,
    DiscoveredLink,
    DiscoveredLinkStatus,
    Document,
    DocumentChunk,
    LocalDataset,
    MockProvider,
    OllamaProvider,
    OutboxEvent,
    OutboxStatus,
    PipelineRun,
    Provider,
    RemoteProvider,
    SourceFetch,
    WebDataset,
)
from backend.shared.storage.sql.models.dataset import DatasetORM
from backend.shared.storage.sql.models.discovered_link import DiscoveredLinkORM
from backend.shared.storage.sql.models.document import DocumentORM
from backend.shared.storage.sql.models.chunk import DocumentChunkORM
from backend.shared.storage.sql.models.outbox_event import OutboxEventORM
from backend.shared.storage.sql.models.pipeline_run import PipelineRunORM
from backend.shared.storage.sql.models.provider import ProviderORM
from backend.shared.storage.sql.models.source_fetch import SourceFetchORM


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
        text_path=orm.text_path,
        created_at=orm.created_at,
        chunks=[_to_chunk(chunk) for chunk in orm.chunks] if include_chunks else [],
    )


def _to_chunk(orm: DocumentChunkORM) -> DocumentChunk:
    return DocumentChunk(
        id=orm.id,
        document_id=orm.document_id,
        text=orm.text,
        chunk_index=orm.chunk_index,
        chunk_type=orm.chunk_type,
        chunk_metadata=orm.chunk_metadata or {},
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
        raw_content_path=orm.raw_content_path,
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


def _to_pipeline_run(orm: PipelineRunORM) -> PipelineRun:
    # The provider snapshot lives inside actor_configs.embed_chunks.provider,
    # not as a top-level column; no separate provider mapping is needed.
    return PipelineRun(
        id=orm.id,
        name=orm.name,
        dataset=dict(orm.dataset or {}),
        actor_configs=dict(orm.actor_configs or {}),
        status=orm.status,
        started_at=orm.started_at,
        finished_at=orm.finished_at,
        created_at=orm.created_at,
    )


def _to_dataset(orm: DatasetORM) -> Dataset:
    if orm.source_type == "web":
        return WebDataset(
            id=orm.id,
            name=orm.name,
            url=orm.url,
            process_child_links=orm.process_child_links,
            process_cross_domain_links=orm.process_cross_domain_links,
            depth=orm.depth,
            created_at=orm.created_at,
        )
    if orm.source_type == "local":
        return LocalDataset(
            id=orm.id,
            name=orm.name,
            paths=list(orm.paths or []),
            created_at=orm.created_at,
        )
    raise ValueError(f"Unknown dataset source_type: {orm.source_type!r}")


def _to_provider(orm: ProviderORM) -> Provider:
    if orm.provider_type == "ollama":
        return OllamaProvider(
            id=orm.id,
            name=orm.name,
            model_type=orm.model_type,
            port=orm.port,
            model_name=orm.model_name,
            created_at=orm.created_at,
        )
    if orm.provider_type == "remote":
        return RemoteProvider(
            id=orm.id,
            name=orm.name,
            model_type=orm.model_type,
            base_url=orm.base_url,
            api_key=orm.api_key,
            organization=orm.organization,
            model_name=orm.model_name,
            created_at=orm.created_at,
        )
    if orm.provider_type == "mock":
        return MockProvider(
            id=orm.id,
            name=orm.name,
            model_type=orm.model_type,
            created_at=orm.created_at,
        )
    raise ValueError(f"Unknown provider_type: {orm.provider_type!r}")
