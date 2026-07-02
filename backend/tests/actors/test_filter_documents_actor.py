from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

import backend.actors.filter_documents_actor.handler as _filter_handler
from backend.actors.filter_documents_actor import filter_documents
from backend.shared.clients.queue.queue_names import PARSE_SOURCE_QUEUE
from backend.shared.models import CrawlTargetStatus, SourceFetch
from backend.tests.actors.pipeline_helpers import (
    make_store,
    make_target,
    outbox_for_queue,
    uow_of,
)

# Minimal valid actor_configs dict for PipelineActorConfigs.model_validate.
_BASE_ACTOR_CONFIGS = {
    "chunk_document": {"strategy": "markdown", "chunk_size": 800, "chunk_overlap": 80},
    "vector_store": {"collection": "test", "similarity": "cosine"},
    "embed_chunks": {"provider": {}},
}

# XML fixtures — use the ``pealkiri`` tag that extract_act_title looks for.
_RELEVANT_XML = "<doc><pealkiri>Income Regulations</pealkiri></doc>"
_NON_RELEVANT_XML = "<doc><pealkiri>General Provisions</pealkiri></doc>"

_FILTER_KEYWORDS = "income,tax"


def _fetch(target_id, *, raw_content_path: str = "_test/raw/content.xml") -> SourceFetch:
    return SourceFetch(
        crawl_target_id=target_id,
        final_url=f"file:///tmp/{target_id}.xml",
        http_status=0,
        content_type="application/xml",
        content_hash="abc",
        raw_content_path=raw_content_path,
    )


def _store_with_keywords(acquired, keywords: str):
    """Build a mock store with a pipeline run that has filter_documents keywords set."""
    store = make_store(acquired=acquired)
    actor_configs = {
        **_BASE_ACTOR_CONFIGS,
        "filter_documents": {"enabled": True, "keywords": keywords},
    }
    mock_run = MagicMock()
    mock_run.actor_configs = actor_configs
    store.pipeline_runs.get.return_value = mock_run
    return store


def test_lock_not_acquired_skips():
    store = make_store(acquired=None)

    filter_documents(crawl_target_id=str(uuid.uuid4()), group="example", store=store)

    store.source_fetches.get_by_crawl_target.assert_not_called()
    store.unit_of_work.assert_not_called()


def test_missing_source_fetch_marks_transient_and_raises():
    target = make_target(status=CrawlTargetStatus.FETCHED)
    store = make_store(acquired=target)
    store.source_fetches.get_by_crawl_target.return_value = None

    with pytest.raises(RuntimeError):
        filter_documents(
            crawl_target_id=str(target.id), group="example", store=store
        )

    assert (
        store.crawl_targets.update_status.call_args.kwargs["status"]
        == CrawlTargetStatus.FAILED_TRANSIENT
    )


def test_relevant_act_advances_to_filtered_and_enqueues_parse(monkeypatch):
    """A document matching the configured keywords is advanced to FILTERED."""
    monkeypatch.setattr(_filter_handler, "read_source_file", lambda p: _RELEVANT_XML)

    target = make_target(status=CrawlTargetStatus.FETCHED)
    pipeline_id = str(uuid.uuid4())
    store = _store_with_keywords(target, _FILTER_KEYWORDS)
    store.source_fetches.get_by_crawl_target.return_value = _fetch(target.id)

    filter_documents(
        crawl_target_id=str(target.id),
        group="example",
        pipeline_id=pipeline_id,
        store=store,
    )

    uow = uow_of(store)
    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.FILTERED)

    parse_events = outbox_for_queue(uow, PARSE_SOURCE_QUEUE)
    assert len(parse_events) == 1
    assert parse_events[0].dedup_key == f"parse:{target.id}"

    store.crawl_targets.update_status.assert_not_called()


def test_non_relevant_act_is_skipped_without_outbox(monkeypatch):
    """A document that does not match the configured keywords is marked SKIPPED."""
    monkeypatch.setattr(_filter_handler, "read_source_file", lambda p: _NON_RELEVANT_XML)

    target = make_target(status=CrawlTargetStatus.FETCHED)
    pipeline_id = str(uuid.uuid4())
    store = _store_with_keywords(target, _FILTER_KEYWORDS)
    store.source_fetches.get_by_crawl_target.return_value = _fetch(target.id)

    filter_documents(
        crawl_target_id=str(target.id),
        group="example",
        pipeline_id=pipeline_id,
        store=store,
    )

    store.crawl_targets.update_status.assert_called_once_with(
        target_id=target.id,
        status=CrawlTargetStatus.SKIPPED,
        skip_reason="not_relevant",
    )
    store.unit_of_work.assert_not_called()


def test_no_keywords_is_passthrough(monkeypatch):
    """When no keywords are configured every document passes through."""
    monkeypatch.setattr(_filter_handler, "read_source_file", lambda p: _NON_RELEVANT_XML)

    target = make_target(status=CrawlTargetStatus.FETCHED)
    # No pipeline_id → cfg is None → FilterDocumentsSettings() with empty keywords.
    store = make_store(acquired=target)
    store.source_fetches.get_by_crawl_target.return_value = _fetch(target.id)

    filter_documents(
        crawl_target_id=str(target.id), group="example", store=store
    )

    # Document passed through — FILTERED via unit_of_work, not SKIPPED.
    uow = uow_of(store)
    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.FILTERED)
    store.crawl_targets.update_status.assert_not_called()


def test_disabled_gate_passes_all_documents(monkeypatch):
    """When the gate is disabled every document passes regardless of keywords."""
    monkeypatch.setattr(_filter_handler, "read_source_file", lambda p: _NON_RELEVANT_XML)

    target = make_target(status=CrawlTargetStatus.FETCHED)
    pipeline_id = str(uuid.uuid4())
    store = make_store(acquired=target)
    actor_configs = {
        **_BASE_ACTOR_CONFIGS,
        "filter_documents": {"enabled": False, "keywords": _FILTER_KEYWORDS},
    }
    mock_run = MagicMock()
    mock_run.actor_configs = actor_configs
    store.pipeline_runs.get.return_value = mock_run
    store.source_fetches.get_by_crawl_target.return_value = _fetch(target.id)

    filter_documents(
        crawl_target_id=str(target.id),
        group="example",
        pipeline_id=pipeline_id,
        store=store,
    )

    uow = uow_of(store)
    uow.set_status.assert_called_once_with(target.id, CrawlTargetStatus.FILTERED)
    store.crawl_targets.update_status.assert_not_called()
