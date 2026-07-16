# Architecture overview

Embeddorium separates orchestration state, source artifacts, dense vectors, and
message transport:

- PostgreSQL is the system of record for datasets, providers, runs, targets,
  documents, chunks, links, outbox events, and search history.
- The filesystem holds raw and parsed source text below a run directory.
- Qdrant stores one vector point per chunk.
- RabbitMQ carries Dramatiq actor messages.
- FastAPI exposes management, retrieval, comparison, and plugin-metadata APIs.
- A React/Vite application calls those APIs.

Ingestion is a set of single-purpose actors. Each actor has a handler containing
the stage logic and a launcher containing Dramatiq, broker, logging, and process
wiring. Downstream stage messages are normally committed to an outbox with the
data they depend on and published by a standalone dispatcher.

Run configuration is stored before work begins. Actors receive a `pipeline_id`
and read the dataset/provider/actor snapshot rather than consulting mutable UI
state.

Retrieval is synchronous in the API server. Semantic search calls the saved
embedding provider and Qdrant; keyword search calls PostgreSQL; hybrid search
calls both and fuses ranks. Search history feeds Search Lab.

Use the focused pages in this section for boundaries, state, and failure
semantics.
