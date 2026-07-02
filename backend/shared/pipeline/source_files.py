"""Keep large raw/parsed text off the Postgres heap; land it as files under the
per-pipeline-run directory instead.

Each pipeline run already owns a directory at
``{PIPELINE_RUNS_DIR}/{pipeline_id}/`` — logs go under ``logs/``, source
artifacts under ``sources/``.  Storing text in files rather than DB columns:

- Avoids bloating the DB with multi-megabyte blobs (raw XML can be several MB
  per document; parsed text is smaller but still non-trivial).
- Keeps all debug/audit artefacts (raw XML, plain-text parse output, per-URL
  log files) together under one run-scoped directory tree that is deleted when
  the run is deleted (``delete_run_files``).
- Survives host/container mount differences because the DB stores only the
  *relative* path (relative to ``PIPELINE_RUNS_DIR``), which resolves
  correctly on any host that mounts the same base directory.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from backend.shared.config import PIPELINE_RUNS_DIR as _PIPELINE_RUNS_DIR_STR

# Module-level variable so tests can monkeypatch it:
#   monkeypatch.setattr(backend.shared.pipeline.source_files, "PIPELINE_RUNS_DIR", tmp_path)
PIPELINE_RUNS_DIR: Path = Path(_PIPELINE_RUNS_DIR_STR)

# Sentinel bucket used when pipeline_id is None (legacy web crawls with no
# associated pipeline run).
_NO_RUN = "_no_run"


def write_source_file(
    *,
    pipeline_id: Optional[str],
    source_id: str,
    kind: str,
    content: str,
    extension: str,
) -> str:
    """Write *content* to disk and return the path relative to PIPELINE_RUNS_DIR.

    The on-disk layout is::

        {PIPELINE_RUNS_DIR}/{pipeline_id}/sources/{source_id}/{kind}/content.{ext}

    Args:
        pipeline_id: The pipeline run ID, or ``None`` for legacy no-run crawls
            (routed to the ``_no_run`` sentinel bucket).
        source_id: Unique identifier for the source, typically
            ``str(crawl_target_id)``.
        kind: Artifact kind — ``"raw"`` (fetched bytes) or ``"parsed"``
            (normalised text output).
        content: The text to persist, written UTF-8.
        extension: File extension **without** a leading dot (e.g. ``"xml"``).

    Returns:
        Relative path string suitable for storage in the DB, e.g.
        ``"{pipeline_id}/sources/{source_id}/raw/content.xml"``.
    """
    bucket = pipeline_id if pipeline_id else _NO_RUN
    rel_path = f"{bucket}/sources/{source_id}/{kind}/content.{extension}"
    abs_path = PIPELINE_RUNS_DIR / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    return rel_path


def read_source_file(relative_path: str) -> str:
    """Read and return the content of a previously-written source file.

    Args:
        relative_path: The path relative to ``PIPELINE_RUNS_DIR`` as stored
            in the DB (e.g.
            ``"{pipeline_id}/sources/{source_id}/raw/content.xml"``).
            A falsy value (``None``, ``""``) returns ``""`` immediately.

    Returns:
        The file's text content decoded as UTF-8 (with ``errors="replace"``),
        or ``""`` when *relative_path* is falsy.
    """
    if not relative_path:
        return ""
    abs_path = PIPELINE_RUNS_DIR / relative_path
    return abs_path.read_text(encoding="utf-8", errors="replace")


def extension_for_content_type(content_type: Optional[str]) -> str:
    """Map an HTTP content-type string to a sensible file extension.

    Matching is substring-based so both ``"application/xml"`` and
    ``"text/xml; charset=utf-8"`` map to ``"xml"``.

    Returns:
        ``"xml"``, ``"html"``, or ``"txt"`` (the catch-all fallback).
    """
    if not content_type:
        return "txt"
    ct = content_type.lower()
    if "xml" in ct:
        return "xml"
    if "html" in ct:
        return "html"
    return "txt"


def run_dir(pipeline_id: str) -> Path:
    """Return the absolute path to a run's root directory.

    Both ``logs/`` and ``sources/`` subdirectories live here.
    """
    return PIPELINE_RUNS_DIR / pipeline_id


def delete_run_files(pipeline_id: str) -> None:
    """Delete all on-disk artefacts for a pipeline run (logs + sources).

    Uses ``ignore_errors=True`` so the call is safe when the directory does not
    exist (e.g. the run was created but never launched, or files were already
    cleaned up).
    """
    shutil.rmtree(run_dir(pipeline_id), ignore_errors=True)
