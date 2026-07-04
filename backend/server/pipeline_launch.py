"""Seed the ingestion pipeline after a ``PipelineRun`` row has been created.

Called by the ``POST /pipeline-runs`` handler after the run row is persisted,
so the row already exists when the first actor message is consumed. This is
the only way pipeline runs are seeded — every run is launched from the UI via
that endpoint, there is no standalone seed script/runner.

Web dataset → publishes one ``crawl_frontier_manager`` message per
``dataset.url``, carrying the run's ``pipeline_id``.

Local dataset → enumerates ``*.xml`` files under each path in
``dataset.paths`` and publishes one ``fetch_file_source`` message per file,
carrying the run's ``pipeline_id``.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import List

import dramatiq

from backend.server.source_root import resolve_for_seed
from backend.shared.clients.queue.process_file_payload import ProcessFileSourcePayload
from backend.shared.clients.queue.process_link_payload import ProcessLinkSourcePayload
from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.clients.queue.queue_names import (
    CRAWL_FRONTIER_MANAGER_ACTOR,
    CRAWL_FRONTIER_MANAGER_QUEUE,
    FETCH_FILE_SOURCE_ACTOR,
    FETCH_FILE_SOURCE_QUEUE,
)

logger = logging.getLogger(__name__)


def ensure_scheme(url: str) -> str:
    """Prepend ``https://`` when no scheme is present."""
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def seed_pipeline(
    *,
    pipeline_id: uuid.UUID,
    dataset_snapshot: dict,
    file_glob: str = "*.xml",
    broker=None,
) -> int:
    """Publish seed messages for the pipeline run identified by *pipeline_id*.

    Returns the number of messages enqueued.

    Parameters
    ----------
    pipeline_id:
        UUID of the already-created ``pipeline_runs`` row.
    dataset_snapshot:
        ``model_dump(mode="json")`` of the dataset; must contain
        ``source_type`` ("web" or "local") plus the type-specific fields.
    file_glob:
        Glob used to enumerate files under a local dataset's folder paths
        (from the run's ``fetch_file_source`` config). Ignored for web datasets.
    broker:
        Dramatiq broker to enqueue on.  When ``None`` a fresh ``QueueClient``
        broker is created (production path); inject a mock in tests.
    """
    if broker is None:
        broker = QueueClient().create("pipeline_launch")
        dramatiq.set_broker(broker)

    source_type = dataset_snapshot.get("source_type")
    pipeline_id_str = str(pipeline_id)
    count = 0

    if source_type == "web":
        count = _seed_web(
            dataset=dataset_snapshot,
            pipeline_id_str=pipeline_id_str,
            broker=broker,
        )
    elif source_type == "local":
        count = _seed_local(
            dataset=dataset_snapshot,
            pipeline_id_str=pipeline_id_str,
            file_glob=file_glob,
            broker=broker,
        )
    else:
        raise ValueError(
            f"Unsupported dataset source_type: {source_type!r}. "
            "Expected 'web' or 'local'."
        )

    logger.info(
        "pipeline_seeded pipeline_id=%s source_type=%s messages=%d",
        pipeline_id_str,
        source_type,
        count,
    )
    return count


def _seed_web(*, dataset: dict, pipeline_id_str: str, broker) -> int:
    """Enqueue a single crawl-frontier message for a web dataset."""
    url = ensure_scheme(dataset.get("url", ""))

    payload = ProcessLinkSourcePayload(
        url=url,
        pipeline_id=pipeline_id_str,
    )
    broker.enqueue(
        dramatiq.Message(
            queue_name=CRAWL_FRONTIER_MANAGER_QUEUE,
            actor_name=CRAWL_FRONTIER_MANAGER_ACTOR,
            args=[],
            kwargs=payload.to_actor_kwargs(),
            options={},
        )
    )
    logger.info(
        "enqueued web seed url=%s pipeline_id=%s", url, pipeline_id_str
    )
    return 1


def _seed_local(
    *, dataset: dict, pipeline_id_str: str, file_glob: str = "*.xml", broker
) -> int:
    """Enumerate matching files and enqueue one fetch-file-source message each.

    Each entry in ``dataset["paths"]`` is one of:
    - A path relative to the source root, as produced by the UI's server-side
      source-file browser (e.g. ``xml.2026.en/act.xml`` for a file, or
      ``xml.2026.en`` for a folder). Relative entries are anchored onto the
      source root so the resulting absolute path matches what the file actor
      sees through its ``./sources`` mount.
    - An absolute path (admin/API use-case), passed through unchanged.

    A ``.xml`` entry is enqueued directly; a directory entry is enumerated
    recursively (``**/*.xml``) so nested subfolders are included. The old
    browser file-picker recorded only bare filenames (``f.name``), which the
    actor could not resolve to a real file — that is why the path looked broken.
    """
    paths: List[str] = dataset.get("paths", [])
    count = 0

    for root_path in paths:
        p = resolve_for_seed(root_path)

        # Directory — enumerate descendants matching the configured glob.
        if p.is_dir():
            xml_files: List[Path] = sorted(p.rglob(file_glob))
        # Individual file — the common file-picker selection. Classified by
        # suffix so a not-yet-on-disk file path is still enqueued.
        elif p.suffix:
            xml_files = [p]
        else:
            logger.warning(
                "local seed path is not a file (no suffix) or an existing "
                "directory, skipping path=%s",
                root_path,
            )
            xml_files = []

        logger.info(
            "xml_files=%s",
            xml_files,
        )

        for file_path in xml_files:
            payload = ProcessFileSourcePayload(
                file_path=str(file_path),
                pipeline_id=pipeline_id_str,
            )
            broker.enqueue(
                dramatiq.Message(
                    queue_name=FETCH_FILE_SOURCE_QUEUE,
                    actor_name=FETCH_FILE_SOURCE_ACTOR,
                    args=[],
                    kwargs=payload.to_actor_kwargs(),
                    options={},
                )
            )
            count += 1

        logger.info(
            "enqueued local seed path=%s files=%d",
            root_path,
            len(xml_files),
        )

    return count
