"""Response schemas for the source-file browse endpoint (``/source-files``)."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel


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
