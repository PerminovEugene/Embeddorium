"""FastAPI app assembly for the Embeddings Matcher API.

Wires together each component's router; the ``/compare`` and ``/search``
route handlers themselves live in their own component packages (see
``backend/server/compare/router.py`` and ``backend/server/search/router.py``).
"""

import logging
from contextlib import asynccontextmanager

import dramatiq
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient

from backend.server.actor_configs.router import router as actor_configs_router
from backend.server.chunkers.router import router as chunkers_router
from backend.server.compare.router import router as compare_router
from backend.server.datasets.router import router as datasets_router
from backend.server.pipeline.router import router as pipeline_router
from backend.server.providers.router import router as providers_router
from backend.server.search.router import router as search_router
from backend.server.source_files.router import router as source_files_router
from backend.shared import config
from backend.shared.clients.queue.queue_client import QueueClient
from backend.shared.storage.sql.sql_store import SqlStore

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the process-wide backing clients on startup and tear them down on
    shutdown: one ``SqlStore`` (engine + pool), one ``QdrantClient`` (HTTP
    pool), and one Dramatiq RabbitMQ broker.

    Handlers reach these through ``Depends(get_sql_store)`` /
    ``Depends(get_qdrant_client)`` / ``Depends(get_broker)`` (see
    ``backend/server/dependencies.py``). Sharing one instance of each lets its
    connection pool actually be reused across requests, instead of each request
    opening and tearing down its own.
    """
    sql_store = SqlStore(application_name="embeddorium-server")
    qdrant_client = QdrantClient(url=config.QDRANT_URL)
    broker = QueueClient().create("embeddorium-server")
    # The server only publishes (never consumes), but set the global broker so
    # any dramatiq machinery that consults it agrees with the one we enqueue on.
    dramatiq.set_broker(broker)

    app.state.sql_store = sql_store
    app.state.qdrant_client = qdrant_client
    app.state.broker = broker
    try:
        yield
    finally:
        sql_store.close()
        qdrant_client.close()
        broker.close()


app = FastAPI(title="Embeddings Matcher API", lifespan=lifespan)

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
app.include_router(actor_configs_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
