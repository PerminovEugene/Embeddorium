"""FastAPI app assembly for the Embeddings Matcher API.

Wires together each component's router; the ``/compare`` and ``/search``
route handlers themselves live in their own component packages (see
``backend/server/compare/router.py`` and ``backend/server/search/router.py``).
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.server.chunkers.router import router as chunkers_router
from backend.server.compare.router import router as compare_router
from backend.server.datasets.router import router as datasets_router
from backend.server.pipeline.router import router as pipeline_router
from backend.server.providers.router import router as providers_router
from backend.server.search.router import router as search_router
from backend.server.source_files.router import router as source_files_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Embeddings Matcher API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compare_router)
app.include_router(search_router)
app.include_router(datasets_router)
app.include_router(providers_router)
app.include_router(pipeline_router)
app.include_router(source_files_router)
app.include_router(chunkers_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
