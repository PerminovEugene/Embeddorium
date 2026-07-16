from __future__ import annotations

from backend.shared.models import (
    Dataset,
    DiscoveredLink,
    DiscoveredLinkStatus,
    Document,
    DocumentChunk,
    LocalDataset,
    OutboxEvent,
    OutboxStatus,
    PipelineRun,
    Provider,
    Search,
    SearchInput,
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
from backend.shared.storage.sql.models.search import SearchORM
from backend.shared.storage.sql.models.search_input import SearchInputORM
from backend.shared.storage.sql.models.source_fetch import SourceFetchORM


def _to_document(orm: DocumentORM, include_chunks: bool = False) -> Document:
    return Document(
        id=orm.id,
        source_url=orm.source_url,
        language=orm.language,
        crawl_target_id=orm.crawl_target_id,
        normalized_url=orm.normalized_url,
        final_url=orm.final_url,
        http_status=orm.http_status,
        content_type=orm.content_type,
        content_hash=orm.content_hash,
        text_hash=orm.text_hash,
        parser_version=orm.parser_version,
        parser_name=orm.parser_name,
        parser_output_format=orm.parser_output_format,
        parser_metadata=dict(orm.parser_metadata or {}),
        parser_intermediate=orm.parser_intermediate,
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
        start_offset=orm.start_offset,
        end_offset=orm.end_offset,
        status=orm.status,
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
        embeddings_scheduled=orm.embeddings_scheduled,
        embeddings_completed=orm.embeddings_completed,
    )


def _to_dataset(orm: DatasetORM) -> Dataset:
    if orm.source_type == "web":
        return WebDataset(
            id=orm.id,
            name=orm.name,
            url=orm.url,
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


def _to_search_input(orm: SearchInputORM) -> SearchInput:
    return SearchInput(
        id=orm.id,
        text=orm.text,
        created_at=orm.created_at,
    )


def _to_search(orm: SearchORM) -> Search:
    return Search(
        id=orm.id,
        pipeline_id=orm.pipeline_id,
        user_input_id=orm.user_input_id,
        search_config=dict(orm.search_config or {}),
        results=list(orm.results or []),
        created_at=orm.created_at,
    )


def _to_provider(orm: ProviderORM) -> Provider:
    return Provider(
        id=orm.id,
        name=orm.name,
        provider_type=orm.provider_type,
        model_type=orm.model_type,
        config=dict(orm.config or {}),
        created_at=orm.created_at,
    )
