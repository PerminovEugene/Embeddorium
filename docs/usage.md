# Usage

This covers the day-to-day: kicking off an ingestion run, querying with the
agent, and using the embeddings tester. For first-time setup see the
[Quick start](../README.md#quick-start) in the README.

## Start a pipeline run

Runs are created through the API — no seed scripts. You need a **dataset** and an
embedding **provider**, both created beforehand via `/datasets` and `/providers`.
Then:

```sh
curl -s -X POST http://localhost:8000/pipeline-runs \
  -H 'Content-Type: application/json' \
  -d '{"datasetId": "<dataset-uuid>", "providerId": "<provider-uuid>"}'
```

You can override chunking and the similarity metric per run:

```json
{
  "datasetId": "<dataset-uuid>",
  "providerId": "<provider-uuid>",
  "actorConfigs": {
    "chunkSize": 1200,
    "chunkOverlap": 150,
    "similarity": "cosine"
  }
}
```

The server then:

1. Loads the dataset and provider (404 if either is missing).
2. Checks the provider is an `embedding` model.
3. Creates the `pipeline_runs` row (`pending`) with full snapshots of both.
4. Publishes the seed message(s) to RabbitMQ carrying `pipeline_id`.
5. Advances the run to `running`.

From there the workers and the outbox dispatcher do the rest. Make sure they're
up (`docker compose up -d`).

## Local XML sources

Local legal-act XML dumps (for example the Estonian `xml.2026.en/` export) live
in the gitignored `sources/` folder at the repo root. It's bind-mounted into the
two services that need it:

| Service | Host path | Container path |
| ------- | --------- | -------------- |
| `worker-fetch-file-source` | `./sources` | `/app/sources` |
| `server` | `./sources` | `/app/sources` |

`worker-fetch-file-source` reads each `.xml` file; the server enumerates the
`*.xml` files from a dataset's configured paths when it publishes the seed
messages.

## The LangGraph agent (optional)

The agent answers questions against the knowledge base you've built, through the
MCP server. Start the MCP server first:

```sh
python -m backend.mcp.server
```

Then ask something (defaults to Ollama):

```sh
python -m backend.agent.generate "What are the VAT rules in Estonia?"

# choose a provider explicitly
python -m backend.agent.generate "What are the VAT rules?" openai

# or via the installed script
laws-generate "What are the VAT rules in Estonia?"
```

The provider can also come from `LLM_PROVIDER` in `.env` instead of the CLI arg.

## Embeddings tester

A small web tool for eyeballing how an embedding model scores text against text:
enter source and candidate texts, pick one or more Ollama models and similarity
metrics, and get back a ranked table of every source/candidate pair. It reuses
the pipeline's own `VectorStore` and embed client, so it stores vectors exactly
like ingestion does.

```sh
docker compose up -d --build qdrant server ui
```

- UI — http://localhost:5173
- API — http://localhost:8000 (docs at `/docs`)

Vectors come from an Ollama server (the port is chosen per request in the UI).
Pull a model first, e.g. `ollama pull nomic-embed-text`. See
[`backend/server/README.md`](../backend/server/README.md) for standalone,
non-Docker usage.

## Handy local endpoints

- Qdrant dashboard — http://localhost:6333/dashboard
- RabbitMQ management — http://localhost:15672
- Postgres — connect with a client like [DBeaver](https://dbeaver.io)
