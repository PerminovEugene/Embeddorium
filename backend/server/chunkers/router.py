"""Read-only metadata endpoint for chunker plugins (``/chunkers``).

Lists every chunker plugin discovered under ``backend/plugins/chunkers`` so
the UI can render a chunker picker and the selected chunker's own settings
form. No DB access — it only reads the in-process plugin registry (see
``backend.plugins.chunkers.registry``).

GET /chunkers — list every discovered chunker's static config.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter

from backend.plugins.chunkers.registry import list_chunker_configs
from backend.server.chunkers.schemas import ChunkerConfigOut, chunker_config_to_out

router = APIRouter(prefix="/chunkers", tags=["chunkers"])


@router.get("", response_model=List[ChunkerConfigOut], response_model_by_alias=True)
async def list_chunkers() -> List[ChunkerConfigOut]:
    """List every discovered chunker plugin's static, UI-facing metadata."""
    return [chunker_config_to_out(cfg) for cfg in list_chunker_configs()]
