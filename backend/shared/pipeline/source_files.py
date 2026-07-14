"""Keep large raw/parsed text off the Postgres heap; land it as files under the
per-pipeline-run directory instead.

Each pipeline run already owns a directory at
``{PIPELINE_RUNS_DIR}/{run-folder}/`` — logs go under ``logs/``, source
artifacts under ``sources/``.  ``{run-folder}`` is ``{pipeline_id}`` optionally
suffixed with the run's slugified name (``{pipeline_id}__{name}``; see
:func:`backend.shared.log_routing.run_folder_name`), so a run's whole tree is
identifiable by name rather than a bare UUID.  Storing text in files rather
than DB columns:

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
from backend.shared.log_routing import run_folder_name

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

        {PIPELINE_RUNS_DIR}/{run-folder}/sources/{source_id}/{kind}/content.{ext}

    where ``{run-folder}`` is the run's named folder (``{pipeline_id}`` or
    ``{pipeline_id}__{name}``; see
    :func:`backend.shared.log_routing.run_folder_name`).  The returned relative
    path is captured at write time and stored verbatim, so it keeps resolving
    even if the folder-name mapping is unavailable later (e.g. on delete).

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
    bucket = run_folder_name(pipeline_id) if pipeline_id else _NO_RUN
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

    Both ``logs/`` and ``sources/`` subdirectories live here. Uses the run's
    named folder when known (``{pipeline_id}__{name}``), else the bare
    ``{pipeline_id}``.
    """
    return PIPELINE_RUNS_DIR / run_folder_name(pipeline_id)


def delete_run_files(pipeline_id: str) -> None:
    """Delete all on-disk artefacts for a pipeline run (logs + sources).

    The run folder may be named ``{pipeline_id}__{name}``, and the caller (the
    API server) does not resolve run names, so every ``{pipeline_id}*`` sibling
    is removed — this also sweeps up any bare-UUID folder left by a process that
    never registered the name. ``ignore_errors=True`` keeps the call safe when a
    directory does not exist (run created but never launched, or already
    cleaned).
    """
    for path in PIPELINE_RUNS_DIR.glob(f"{pipeline_id}*"):
        shutil.rmtree(path, ignore_errors=True)
