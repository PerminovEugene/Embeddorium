# Providers

A provider is a saved model endpoint and capability:

```text
Provider { id, name, provider_type, model_type, config, created_at }
```

`provider_type` identifies a discovered adapter. `model_type` identifies the
capability. The flat `config` JSON object is validated against the connection
fields from the adapter plus the fields from the selected capability handler.

## Built-in provider types

| Type | Capability | Configuration |
| --- | --- | --- |
| `mock` | `embedding` | `mock_dim` (default `4096`) |
| `ollama` | `embedding` | `url`, `port`, `model_name` |
| `ollama` | `cross-encoder` | `url`, `port`, `model_name`, `rerank_path` |
| `openai` | `embedding` | `url`, optional `port`, optional `api_key`, `model_name` |

The defaults are published by `GET /providers/configs`. Ollama defaults to the
embedding base URL split into URL and port and model `qwen3-embedding`.
OpenAI defaults to `https://api.openai.com/v1` and
`text-embedding-3-small`.

## Provider snapshots

An ingestion run requires a provider whose `model_type` is `embedding`. The
entire provider record is stored at
`actor_configs.embed_chunks.provider`. Ingestion and semantic query embedding
both resolve clients from that snapshot.

Hybrid reranking instead accepts the ID of a current `cross-encoder` provider
at search time; it is not part of the ingestion snapshot.

## Networking

Provider URLs must be reachable from the process making the request. The
embedding worker and API server run in containers under Compose. A model on a
Docker Desktop host is normally reached through `host.docker.internal`, not
`localhost`.

The `OPENAI_API_KEY` agent environment variable is separate from the API key
stored in an OpenAI embedding provider.
