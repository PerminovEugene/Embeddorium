# Tutorial: your first pipeline run (mock provider)

## Goal

Go from a fresh clone to a **completed pipeline run** and a **Qdrant collection**
using the `mock` embedding provider — no model, no external services, done in a
couple of minutes. The mock provider produces random vectors, so this verifies
the *pipeline*, not retrieval quality — exactly what you want for a first run.

## Prerequisites

- Docker with Compose v2 (`docker compose`).
- Git.
- Ports `5173`, `8000`, `6333`, `5432`, `5672`, `15672` free.

## Step 1 — Start the stack

```sh
git clone <repo-url> embeddorium && cd embeddorium
cp .env.example .env
docker compose up -d --build
```

Migrations run automatically (the `migrate` service runs before the workers).
Wait until everything is up:

```sh
docker compose ps
```

## Step 2 — Open the UI

Go to **http://localhost:5173**. Keep the Qdrant dashboard handy in another tab:
**http://localhost:6333/dashboard**.

## Step 3 — Create a dataset (source)

A **dataset** describes where content comes from. Go to **Datasets** → **Create**
and make a **Web** dataset:

- **Name:** anything, e.g. `example-single-page`.
- **URL:** a single page, e.g. `https://example.com`.
- **Depth:** `0` — fetch just that page, follow no links.
- Leave child / cross-domain link options off.

Save. (Prefer local files instead of the web? See the
[local XML import tutorial](local_xml_import.md).)

## Step 4 — Create a mock provider

The embedding provider is chosen **per run**, so create one first. Go to
**Providers** → **Create**:

- **Type:** **Mock**.
- **Model type:** **embedding**.
- **Name:** e.g. `mock-embed`.

Save. The mock provider needs no model, URL, or key.

## Step 5 — Launch a pipeline run

Go to **Pipeline runs** → start a new run:

- **Dataset:** the one from Step 3.
- **Provider:** the mock provider from Step 4.
- (Optional) override **chunk size / overlap** — defaults are fine.

Launch it. The run is created, seeded, and advances to `running`.

## Step 6 — Inspect artifacts and chunks

Within a few seconds the run should reach **`completed`** with a `finishedAt`
timestamp. While it runs (or after), look at what each stage produced on the
host:

```sh
ls tmp/pipeline_run/<run-id>/
ls tmp/pipeline_run/<run-id>/sources/<source-id>/raw/     # raw fetched bytes
ls tmp/pipeline_run/<run-id>/sources/<source-id>/parsed/  # normalized text
```

Postgres holds the structured records — `documents`, `document_chunks`,
`crawl_targets`, and the run row itself. You can browse them via the API docs at
http://localhost:8000/docs (`GET /pipeline-runs/<id>`).

## Step 7 — Verify the Qdrant collection

Open the Qdrant dashboard: **http://localhost:6333/dashboard**. A new
**collection** for this run should be listed, holding one point per chunk (keyed
by chunk id). Or from the host:

```sh
curl -s http://localhost:6333/collections
```

**You're done** when the run shows `completed` in the UI and its collection
exists in Qdrant.

## Cleanup / reset

Wipe all local state and start fresh:

```sh
scripts/full-clean.sh
```

Or tear the stack down completely:

```sh
docker compose down -v
```

## Next steps

- Swap in real embeddings: [Ollama embeddings tutorial](ollama_embeddings.md).
- Ingest local files: [local XML import tutorial](local_xml_import.md).
- Crawl a site: [web crawl tutorial](web_crawl.md).

## Appendix — do it over the API

Every UI action is a REST call (interactive docs at
http://localhost:8000/docs). The provider/dataset bodies use camelCase.

```sh
# 1. Create a mock embedding provider
PROVIDER_ID=$(curl -s -X POST http://localhost:8000/providers \
  -H 'Content-Type: application/json' \
  -d '{"name":"mock-embed","providerType":"mock","modelType":"embedding"}' \
  | python -c 'import sys,json; print(json.load(sys.stdin)["id"])')

# 2. Create a single-page web dataset
DATASET_ID=$(curl -s -X POST http://localhost:8000/datasets \
  -H 'Content-Type: application/json' \
  -d '{"name":"example-single-page","sourceType":"web","url":"https://example.com","processChildLinks":false,"processCrossDomainLinks":false,"depth":0}' \
  | python -c 'import sys,json; print(json.load(sys.stdin)["id"])')

# 3. Start the run
curl -s -X POST http://localhost:8000/pipeline-runs \
  -H 'Content-Type: application/json' \
  -d "{\"datasetId\":\"$DATASET_ID\",\"providerId\":\"$PROVIDER_ID\"}"

# 4. Poll the run until it reports "completed"
curl -s http://localhost:8000/pipeline-runs
```
