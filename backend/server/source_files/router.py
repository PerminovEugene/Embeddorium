"""Browse endpoint for the ingestion source tree (``/source-files``).

Browsers cannot hand back real filesystem paths for picked files (only the bare
name), so the UI cannot map a file-input selection onto a file inside the
mounted source dir. Instead, the UI browses the source tree *server-side* via
this endpoint and stores the chosen entries as paths relative to the source
root — paths the pipeline seeder can resolve back to real files.

Only directories and ``.xml`` files are listed, since the file-ingestion chain
only consumes XML acts. All returned paths are relative to the source root.

Thin controller: the walk logic lives in ``source_files.service``.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.server.source_files.schemas import SourceListing
from backend.server.source_files.service import list_source_entries

router = APIRouter(prefix="/source-files", tags=["source-files"])


@router.get("", response_model=SourceListing)
async def list_source_files(
    path: str = Query(
        "", description="Directory to list, relative to the source root."
    ),
) -> SourceListing:
    """List the directories and ``.xml`` files directly under *path*."""
    return list_source_entries(path)
