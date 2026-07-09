"""Route handlers for the ``/search`` and ``/searches`` endpoints."""

import uuid

from fastapi import APIRouter, HTTPException

from backend.server.search.history import get_search, list_searches
from backend.server.search.schemas import (
    SearchDetailOut,
    SearchRequest,
    SearchSummaryOut,
)
from backend.server.search.service import search_db

router = APIRouter(tags=["search"])


@router.post("/search")
async def search(request: SearchRequest):
    """Embed each source text and return its nearest vectors from the selected
    pipeline run's collection, enriched with chunk/document info from Postgres."""
    return await search_db(request)


@router.get("/searches", response_model=list[SearchSummaryOut])
async def search_history():
    """List persisted search launches (newest first), without result hits."""
    return list_searches()


@router.get("/searches/{search_id}", response_model=SearchDetailOut)
async def search_history_detail(search_id: uuid.UUID):
    """One persisted search including its stored result hits."""
    detail = get_search(search_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Unknown search")
    return detail
