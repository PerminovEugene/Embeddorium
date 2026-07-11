"""Route handlers for the ``/search`` and ``/searches`` endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from qdrant_client import QdrantClient

from backend.server.dependencies import get_qdrant_client, get_sql_store
from backend.server.search.history import get_search, list_searches
from backend.server.search.schemas import (
    SearchDetailOut,
    SearchRequest,
    SearchSummaryOut,
)
from backend.server.search.service import search_db
from backend.shared.storage.sql.sql_store import SqlStore

router = APIRouter(tags=["search"])


@router.post("/search")
async def search(
    request: SearchRequest,
    store: SqlStore = Depends(get_sql_store),
    qdrant: QdrantClient = Depends(get_qdrant_client),
):
    """Embed each source text and return its nearest vectors from the selected
    pipeline run's collection, enriched with chunk/document info from Postgres."""
    return await search_db(store, qdrant, request)


@router.get("/searches", response_model=list[SearchSummaryOut])
async def search_history(store: SqlStore = Depends(get_sql_store)):
    """List persisted search launches (newest first), without result hits."""
    return list_searches(store)


@router.get("/searches/{search_id}", response_model=SearchDetailOut)
async def search_history_detail(
    search_id: uuid.UUID, store: SqlStore = Depends(get_sql_store)
):
    """One persisted search including its stored result hits."""
    detail = get_search(store, search_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Unknown search")
    return detail
