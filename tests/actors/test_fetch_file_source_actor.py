import uuid
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

from laws_agent.actors.fetch_file_source_actor import fetch_file_source
from laws_agent.clients.queue.queue_names import FILTER_TAX_ACTS_QUEUE
from laws_agent.models import CrawlTarget, CrawlTargetStatus
from tests.actors.pipeline_helpers import outbox_for_queue, uow_of


def _make_store(*, existing_target=None) -> MagicMock:
    store = MagicMock()
    store.crawl_targets.find_active_by_normalized_url.return_value = existing_target

    saved_targets: List[CrawlTarget] = []

    def _save(target: CrawlTarget) -> CrawlTarget:
        persisted = target.model_copy(update={"id": uuid.uuid4()})
        saved_targets.append(persisted)
        return persisted

    store.crawl_targets.save.side_effect = _save
    store.saved_targets = saved_targets

    uow = MagicMock()
    cm = store.unit_of_work.return_value
    cm.__enter__.return_value = uow
    cm.__exit__.return_value = False
    return store


def test_reads_file_and_saves_target_and_fetch(tmp_path: Path) -> None:
    file_path = tmp_path / "501012020001.xml"
    file_path.write_text("<oigusakt><pealkiri>Income Tax Act</pealkiri></oigusakt>")
    store = _make_store()

    fetch_file_source(file_path=str(file_path), group="Estonia", store=store)

    store.crawl_targets.save.assert_called_once()
    saved = store.saved_targets[-1]
    assert saved.original_url == str(file_path.resolve())
    assert saved.normalized_url == f"file://{file_path.resolve()}"
    assert saved.group == "Estonia"
    assert saved.status == CrawlTargetStatus.FETCHING
    assert saved.log_dir is not None


def test_writes_source_fetch_advances_status_and_enqueues_filter(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "501012020001.xml"
    content = "<oigusakt><pealkiri>Income Tax Act</pealkiri></oigusakt>"
    file_path.write_text(content)
    store = _make_store()

    fetch_file_source(file_path=str(file_path), group="Estonia", store=store)

    saved = store.saved_targets[-1]

    uow = uow_of(store)
    uow.upsert_source_fetch.assert_called_once()
    fetch = uow.upsert_source_fetch.call_args.args[0]
    assert fetch.crawl_target_id == saved.id
    assert fetch.raw_content == content
    assert fetch.content_type == "application/xml"
    assert fetch.http_status == 0
    assert fetch.content_hash

    uow.set_status.assert_called_once_with(saved.id, CrawlTargetStatus.FETCHED)

    filter_events = outbox_for_queue(uow, FILTER_TAX_ACTS_QUEUE)
    assert len(filter_events) == 1
    assert filter_events[0].dedup_key == f"filter:{saved.id}"


def test_dedup_skips_when_target_already_active(tmp_path: Path) -> None:
    file_path = tmp_path / "501012020001.xml"
    file_path.write_text("<oigusakt/>")
    existing = CrawlTarget(
        group="Estonia",
        original_url=str(file_path.resolve()),
        normalized_url=f"file://{file_path.resolve()}",
        status=CrawlTargetStatus.FETCHED,
    )
    store = _make_store(existing_target=existing)

    fetch_file_source(file_path=str(file_path), group="Estonia", store=store)

    store.crawl_targets.save.assert_not_called()
    store.unit_of_work.assert_not_called()


def test_second_run_with_same_path_is_deduped(tmp_path: Path) -> None:
    """End-to-end-ish: simulate the second call seeing the first call's save."""
    file_path = tmp_path / "501012020001.xml"
    file_path.write_text("<oigusakt><pealkiri>Customs Act</pealkiri></oigusakt>")
    store = _make_store()

    fetch_file_source(file_path=str(file_path), group="Estonia", store=store)
    first_saved = store.saved_targets[-1]

    # Second message for the same file: dedup lookup now returns the target
    # created by the first call.
    store.crawl_targets.find_active_by_normalized_url.return_value = first_saved

    fetch_file_source(file_path=str(file_path), group="Estonia", store=store)

    assert store.crawl_targets.save.call_count == 1


def test_missing_file_marks_failed_permanent(tmp_path: Path) -> None:
    missing_path = tmp_path / "does-not-exist.xml"
    store = _make_store()

    fetch_file_source(file_path=str(missing_path), group="Estonia", store=store)

    saved = store.saved_targets[-1]
    store.crawl_targets.update_status.assert_called_once()
    assert (
        store.crawl_targets.update_status.call_args.kwargs["status"]
        == CrawlTargetStatus.FAILED_PERMANENT
    )
    assert store.crawl_targets.update_status.call_args.kwargs["target_id"] == saved.id
    store.unit_of_work.assert_not_called()


def test_relative_path_is_normalized_to_absolute(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "501012020001.xml"
    file_path.write_text("<oigusakt/>")
    monkeypatch.chdir(tmp_path)
    store = _make_store()

    fetch_file_source(file_path=file_path.name, group="Estonia", store=store)

    saved = store.saved_targets[-1]
    assert saved.original_url == str(file_path.resolve())
    assert Path(saved.original_url).is_absolute()
