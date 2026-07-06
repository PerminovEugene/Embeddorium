"""Route handler for the ``/search`` endpoint."""

from fastapi import APIRouter

from backend.server.search.schemas import SearchRequest
from backend.server.search.service import search_db

router = APIRouter(tags=["search"])


@router.post("/search")
async def search(request: SearchRequest):
    """Embed each source text and return its nearest vectors from the selected
    pipeline run's collection, enriched with chunk/document info from Postgres."""
    return await search_db(request)
