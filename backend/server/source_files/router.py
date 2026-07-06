"""Browse endpoint for the ingestion source tree (``/source-files``).

Browsers cannot hand back real filesystem paths for picked files (only the bare
name), so the UI cannot map a file-input selection onto a file inside the
mounted source dir. Instead, the UI browses the source tree *server-side* via
this endpoint and stores the chosen entries as paths relative to the source
root — paths the pipeline seeder can resolve back to real files.

Only directories and ``.xml`` files are listed, since the file-ingestion chain
only consumes XML acts. All returned paths are relative to the source root.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.server.source_files.source_root import (
    get_source_root,
    safe_resolve_within_root,
)

router = APIRouter(prefix="/source-files", tags=["source-files"])

# Only XML acts are ingestable; hide everything else to keep the picker honest.
_XML_SUFFIX = ".xml"


class SourceEntry(BaseModel):
    """A single browseable item: a subdirectory or an .xml file."""

    name: str
    # Path relative to the source root (forward-slashed); this is what the UI
    # stores in ``dataset.paths`` and the seeder resolves back to a real file.
    path: str
    type: Literal["dir", "file"]


class SourceListing(BaseModel):
    """Contents of one directory level, plus navigation breadcrumbs."""

    # Current directory, relative to the source root ("" at the root).
    path: str
    # Parent directory relative path, or null when already at the root.
    parent: Optional[str]
    entries: List[SourceEntry]


def _rel(child: Path, root: Path) -> str:
    """Forward-slashed path of *child* relative to *root*."""
    return child.relative_to(root).as_posix()


@router.get("", response_model=SourceListing)
async def list_source_files(
    path: str = Query("", description="Directory to list, relative to the source root."),
) -> SourceListing:
    """List the directories and ``.xml`` files directly under *path*."""
    root = get_source_root()
    try:
        target = safe_resolve_within_root(path)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")

    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    dirs: List[SourceEntry] = []
    files: List[SourceEntry] = []
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
