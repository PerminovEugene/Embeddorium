# Providers

A **provider** is a configured model backend a run can use — an Ollama server,
an OpenAI-compatible API, or the in-process `mock`. This is the single reference
for how providers are modelled, which types exist, and how to configure each
one. It covers embedding providers (used by the ingestion pipeline) as well as
the reranker capability used by hybrid search.

## The model: provider type + model type

A saved provider is a **flat record** (`backend/shared/models/provider.py`):

```
Provider { provider_type, model_type, config }
```

- **`provider_type`** — the runtime/API you talk to (`mock`, `ollama`,
  `openai`). It owns the *connection*: the `url` / `port` / `api_key` shared by
  every model that backend serves. Each provider type is an adapter under
  `backend/plugins/provider_types/<name>/`.
- **`model_type`** — the *capability* the model serves (`embedding`,
  `cross-encoder`). It owns the capability-specific settings (`model_name`,
  `mock_dim`, `rerank_path`).
- **`config`** — one JSONB blob validated against the **union** of the provider
  type's connection fields and the selected model type's fields.

This two-level shape means a cross-encoder reranker is a *model type* offered
under a provider (e.g. `ollama`), not a provider type of its own, and adding a
new backend is a new adapter folder — no change to the `Provider` model. See
`backend/plugins/provider_types/base.py` for the adapter interfaces.

## How a run uses a provider

Providers are selected **per run**, not globally. When you create a pipeline
run, the embedding provider you pick is snapshotted into the run's
`actor_configs.embed_chunks.provider` (`EmbedChunksSettings.provider`). The
`embed_chunks` actor reads that immutable snapshot and builds the embed client
through the provider registry — so the index side and the query (search) side
always agree on exactly one provider/model, even across concurrent runs with
different settings.

The `EMBED_PROVIDER` / `OLLAMA_EMBED_*` environment variables
([configuration.md](configuration.md#embeddings)) are **only the fallback** for
a run that carries no provider snapshot; a normally-created run never reads them.

Every provider is remote/API (`ollama`, `openai`) or the trivial in-process
`mock`. Embeddorium never loads an embedding model in-process, so the worker
container stays light — no `torch` / `onnxruntime` / `sentence-transformers`.

## Provider types

| Provider type | Where it runs | Connection fields | Capabilities (model types) |
| ------------- | ------------- | ----------------- | -------------------------- |
| `mock` | in-process (`builtin`) | none | `embedding` |
| `ollama` | remote HTTP (`remote`) | `url`, `port` (no key) | `embedding`, `cross-encoder` |
| `openai` | remote HTTP (`remote`) | `url`, `port`, `api_key` | `embedding` |

Field defaults come from the adapter (and, for a few, env vars) and are filled in
when you leave a form field blank.

---

## `mock` — fast, meaningless vectors

Returns random vectors of a fixed dimension. It loads no model and touches no
network, so embedding finishes almost instantly and the container image stays
tiny. Use it to exercise the **whole pipeline end to end** without waiting on a
model. Retrieval results are random, so this verifies the flow, not query
quality.

- **Connection:** none.
- **`embedding` field:** `mock_dim` — the vector dimension. It must match the
  collection the run indexed into. Defaults to `MOCK_EMBED_DIM` (`4096`, the
  Qwen3-Embedding-8B dimension).

Env fallback:

```sh
EMBED_PROVIDER=mock
MOCK_EMBED_DIM=4096   # optional
```

## `ollama` — local/LAN Ollama over HTTP

Calls an Ollama server over HTTP (via `langchain-ollama`). No API key — Ollama is
unauthenticated. Pull the model once on whichever host runs Ollama:

```sh
ollama pull qwen3-embedding
```

- **Connection fields:** `url` (default from `OLLAMA_URL` / the embed base URL),
  `port` (default `11434`).
- **`embedding` field:** `model_name` (default `OLLAMA_EMBED_MODEL`, e.g.
  `qwen3-embedding`).
- **`cross-encoder` fields** (reranker for hybrid search): `model_name` (default
  `BAAI/bge-reranker-v2-m3`) and `rerank_path` — the rerank endpoint path, which
  differs by server (vLLM `v1/rerank`, Infinity `rerank`; default from
  `RERANKER_PATH`). The reranker is a networked service (vLLM / Infinity / TEI /
  Cohere-style), pointed at by the provider's `url`/`port`.

Env fallback:

```sh
EMBED_PROVIDER=ollama
OLLAMA_EMBED_MODEL=qwen3-embedding
OLLAMA_EMBED_BASE_URL=http://host.docker.internal:11434   # see below
```

### Pointing a container at Ollama

`OLLAMA_EMBED_BASE_URL` (and the `url` on an Ollama provider record) has to be
reachable from **inside** the `worker-embed-chunks` container.
`http://localhost:11434` will not work there — each container has its own
loopback, separate from the host's.

**Ollama on the host** (e.g. natively on a Mac, for Metal acceleration). Pull the
model on the host, then point the container at the host's special DNS name:

```sh
ollama pull qwen3-embedding   # on the host, not in a container
```

```sh
# .env.docker
OLLAMA_EMBED_BASE_URL=http://host.docker.internal:11434
```

On Linux without Docker Desktop, use the Docker bridge IP (e.g.
`http://172.17.0.1:11434`) or add
`extra_hosts: ["host.docker.internal:host-gateway"]` to the service.

**Ollama in your own container.** If you run Ollama in Docker yourself, attach it
to this project's Compose network and use its container name as the host (e.g.
`http://ollama:11434`).

## `openai` — remote OpenAI-compatible API

Calls an OpenAI-compatible embeddings endpoint over HTTP with an API key. Like
`ollama` it is transport-only — no in-process model — so the worker stays light.

- **Connection fields:** `url` (default `https://api.openai.com/v1`, override
  with `OPENAI_BASE_URL`), `port` (default none), `api_key`.
- **`embedding` field:** `model_name` (default `text-embedding-3-small`).

Configure it per run through a saved provider record rather than the env
fallback.

---

## The chat agent uses its own settings

The optional LangGraph chat agent has a **separate** provider configuration
(`LLM_PROVIDER`, `OLLAMA_BASE_URL`, `OPENAI_MODEL`, …) that is independent from
the embedding providers above — see
[configuration.md](configuration.md#chat-agent). The two `OLLAMA_*_BASE_URL`
variables are deliberately distinct: embeddings use `OLLAMA_EMBED_BASE_URL`
(from a container), the agent uses `OLLAMA_BASE_URL` (from the host).
</content>
