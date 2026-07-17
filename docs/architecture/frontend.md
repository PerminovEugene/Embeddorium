# Frontend architecture

The UI is a React 19 single-page application built with TypeScript and Vite 6.
It calls the FastAPI server at `VITE_SERVER_URL`, defaulting to
`http://localhost:8000`. The dev server itself listens on `UI_PORT`
(default `5173`), which the backend also uses to build its CORS allowlist.

## Routes

| Path | Header label | Purpose |
| --- | --- | --- |
| `/` | Search | Manual embedding comparison or run-scoped retrieval |
| `/search-comparison` | Search Lab | Compare persisted search results |
| `/datasets` | Datasets | Create/view/delete source definitions |
| `/providers` | LLM Providers | Create/view/delete provider configs |
| `/ingestion-pipelines` | Pipelines | Create, inspect, launch, relaunch, delete runs |
| `/pipeline-runs` | Indexing Runs | Poll and inspect run/target progress |

## Data flow

API modules under `ui/src/api` translate camelCase HTTP objects into UI types.
Nested run snapshots remain snake_case because the backend returns raw JSON
model dumps in those blocks.

Dataset and provider forms become read-only after creation; their pages offer
delete rather than edit, despite PUT endpoints existing in the backend.
Pipeline creation can select multiple datasets; the client sends one create
request per dataset with the same actor settings.

Actor and provider controls are partially metadata-driven:

- `GET /actor-configs` supplies plugin field definitions.
- `GET /providers/configs` supplies provider connection and model-type fields.
- Schedule-embedding, link-scheduling, and vector similarity controls remain
  hardcoded in the frontend.

The Search form stores inputs and preferences in browser `localStorage`, but
not result arrays. Indexing Runs polls running selections every 10 seconds.
