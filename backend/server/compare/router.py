"""Route handler for the ``/compare`` endpoint.

Thin controller: it delegates to ``compare.service.compare_embeddings``, which
embeds the user's source and candidate texts with the selected provider and
scores every source/candidate pair with the requested similarity metrics.
"""

from fastapi import APIRouter, Depends

from backend.server.compare.schemas import CompareRequest
from backend.server.compare.service import compare_embeddings
from backend.server.dependencies import get_sql_store
from backend.shared.storage.sql.sql_store import SqlStore

router = APIRouter(tags=["compare"])


@router.post("/compare")
async def compare(request: CompareRequest, store: SqlStore = Depends(get_sql_store)):
    return await compare_embeddings(store, request)
