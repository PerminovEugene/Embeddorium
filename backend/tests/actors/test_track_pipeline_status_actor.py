import uuid
from datetime import datetime
from unittest.mock import MagicMock

from backend.actors.track_pipeline_status_actor import track_pipeline_status
from backend.shared.models import PipelineRun


def _make_run(
    *,
    run_id: uuid.UUID,
    status: str = "running",
    embeddings_scheduled: int = 0,
    embeddings_completed: int = 0,
) -> PipelineRun:
    return PipelineRun(
        id=run_id,
        dataset={"name": "test-dataset", "source_type": "web", "url": "https://x"},
        actor_configs={
            "chunk_document": {"chunker": "text_markdown", "settings": {}},
            "vector_store": {"collection": "test", "similarity": "cosine"},
            "embed_chunks": {"provider": {"provider_type": "mock"}},
        },
        status=status,
        embeddings_scheduled=embeddings_scheduled,
        embeddings_completed=embeddings_completed,
    )


def _make_store(*, run: PipelineRun, active_targets: int = 0) -> MagicMock:
    store = MagicMock()
    store.pipeline_runs.get.return_value = run
    store.crawl_targets.count_active_for_pipeline.return_value = active_targets
    store.pipeline_runs.complete_if_running.return_value = run
    return store


def test_missing_run_is_skipped() -> None:
    store = MagicMock()
    store.pipeline_runs.get.return_value = None

    track_pipeline_status(pipeline_id=str(uuid.uuid4()), store=store)

    store.crawl_targets.count_active_for_pipeline.assert_not_called()
    store.pipeline_runs.complete_if_running.assert_not_called()


def test_run_not_running_is_skipped() -> None:
    run_id = uuid.uuid4()
    run = _make_run(run_id=run_id, status="completed")
    store = _make_store(run=run)

    track_pipeline_status(pipeline_id=str(run_id), store=store)

    store.crawl_targets.count_active_for_pipeline.assert_not_called()
    store.pipeline_runs.complete_if_running.assert_not_called()


def test_active_targets_remaining_blocks_completion() -> None:
    run_id = uuid.uuid4()
    run = _make_run(
        run_id=run_id, status="running", embeddings_scheduled=3, embeddings_completed=3
    )
    store = _make_store(run=run, active_targets=1)

    track_pipeline_status(pipeline_id=str(run_id), store=store)

    store.pipeline_runs.complete_if_running.assert_not_called()


def test_incomplete_embeddings_blocks_completion() -> None:
    run_id = uuid.uuid4()
    run = _make_run(
        run_id=run_id, status="running", embeddings_scheduled=3, embeddings_completed=2
    )
    store = _make_store(run=run, active_targets=0)

    track_pipeline_status(pipeline_id=str(run_id), store=store)

    store.pipeline_runs.complete_if_running.assert_not_called()


def test_no_active_targets_and_all_embeddings_done_completes_run() -> None:
    run_id = uuid.uuid4()
    run = _make_run(
        run_id=run_id, status="running", embeddings_scheduled=3, embeddings_completed=3
    )
    store = _make_store(run=run, active_targets=0)

    track_pipeline_status(pipeline_id=str(run_id), store=store)

    store.pipeline_runs.complete_if_running.assert_called_once()
    args, kwargs = store.pipeline_runs.complete_if_running.call_args
    assert args[0] == run_id
    assert isinstance(kwargs["finished_at"], datetime)
    assert kwargs["finished_at"].tzinfo is not None


def test_zero_scheduled_zero_completed_still_completes_run() -> None:
    # A run whose every target was filtered/failed schedules no embeds at
    # all; embeddings_completed >= embeddings_scheduled still holds at 0 >= 0.
    run_id = uuid.uuid4()
    run = _make_run(
        run_id=run_id, status="running", embeddings_scheduled=0, embeddings_completed=0
    )
    store = _make_store(run=run, active_targets=0)

    track_pipeline_status(pipeline_id=str(run_id), store=store)

    store.pipeline_runs.complete_if_running.assert_called_once()
