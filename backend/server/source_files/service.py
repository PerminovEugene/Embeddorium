"""Service layer for browsing the ingestion source tree (``/source-files``).

Walks one directory level under the source root, exposing only subdirectories
and ``.xml`` files (the only ingestable acts), with every path returned relative
to the source root. The route handler is a thin controller over
``list_source_entries``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from backend.server.source_files.schemas import SourceEntry, SourceListing
from backend.server.source_files.source_root import (
    get_source_root,
    safe_resolve_within_root,
)

# Only XML acts are ingestable; hide everything else to keep the picker honest.
_XML_SUFFIX = ".xml"


def _rel(child: Path, root: Path) -> str:
    """Forward-slashed path of *child* relative to *root*."""
    return child.relative_to(root).as_posix()


def list_source_entries(path: str) -> SourceListing:
    """List the directories and ``.xml`` files directly under *path*.

    Raises 400 if *path* escapes the source root and 404 if it isn't an existing
    directory.
    """
    root = get_source_root()
    try:
        target = safe_resolve_within_root(path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")

    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    dirs: list[SourceEntry] = []
    files: list[SourceEntry] = []
    for child in target.iterdir():
        if child.is_dir():
            dirs.append(
                SourceEntry(name=child.name, path=_rel(child, root), type="dir")
            )
        elif child.is_file() and child.suffix.lower() == _XML_SUFFIX:
            files.append(
                SourceEntry(name=child.name, path=_rel(child, root), type="file")
            )

    dirs.sort(key=lambda e: e.name.lower())
    files.sort(key=lambda e: e.name.lower())

    # "" relative path means the listed dir is the root, which has no parent.
    rel_path = _rel(target, root) if target != root else ""
    parent = None if not rel_path else Path(rel_path).parent.as_posix()
    if parent == ".":
        parent = ""

    return SourceListing(path=rel_path, parent=parent, entries=dirs + files)
