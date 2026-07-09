# Tutorial: real local embeddings with Ollama

## Goal

Replace the `mock` provider with real, locally-computed embeddings from an
[Ollama](https://ollama.com) server, so retrieval results are meaningful. Assumes
you've done the [first mock run](first_mock_run.md) and the stack is up.

The embed worker calls Ollama over HTTP via thin `httpx`/`langchain-ollama`
clients — no `torch`, no `sentence-transformers` in the container. For the full
provider reference and networking matrix, see [../embeddings.md](../embeddings.md).

## Step 1 — Run Ollama and pull an embedding model

Install Ollama and pull an **embedding** model (not a chat model):

```sh
ollama pull qwen3-embedding
ollama list          # confirm it's present
```

Any Ollama embedding model works (e.g. `nomic-embed-text`) — just match the name
in the provider config below.

## Step 2 — Make Ollama reachable from the container

The embed worker runs in a container, so `http://localhost:11434` points at the
**container's** loopback, not your host. Pick one:

**A. Ollama on the host (Docker Desktop, Mac/Windows).** Use the special DNS name:

```sh
# .env.docker
OLLAMA_EMBED_BASE_URL=http://host.docker.internal:11434
```

**B. Ollama in your own Docker container.** Attach it to this project's Compose
network and use its container name as the host:

```sh
# .env.docker
OLLAMA_EMBED_BASE_URL=http://ollama:11434
```

**C. Linux without Docker Desktop.** Use the Docker bridge IP (e.g.
`http://172.17.0.1:11434`) or add
`extra_hosts: ["host.docker.internal:host-gateway"]` to the service.

`OLLAMA_EMBED_BASE_URL` / `OLLAMA_EMBED_MODEL` in `.env.docker` are the **fallback**
for runs that carry no provider snapshot. The per-run provider you create below
is what actually drives a run. After editing `.env.docker`, restart the worker:

```sh
docker compose up -d worker-embed-chunks
```

## Step 3 — Create an Ollama provider

In the UI → **Providers** → **Create**:

- **Type:** **Ollama**.
- **Model type:** **embedding**.
- **Model name:** `qwen3-embedding` (must match what you pulled).
- **Port:** the port Ollama listens on (default `11434`).
- **Name:** e.g. `ollama-qwen3`.

Save.

> The provider's host is resolved by the worker via `OLLAMA_EMBED_BASE_URL`; the
> provider record supplies the **model** and **port**. Keep them consistent with
> Step 2.

## Step 4 — Run and confirm embeddings are generated

Start a **Pipeline run** with your dataset and the **Ollama** provider. Then
confirm real embeddings are flowing:

```sh
# The embed worker logs each batch it embeds
docker compose logs -f worker-embed-chunks

# Reachability check from inside the container
docker compose exec worker-embed-chunks \
  curl -s http://host.docker.internal:11434/api/tags
```

When the run reaches **`completed`**, open the Qdrant dashboard
(http://localhost:6333/dashboard): the collection's vector dimension will match
the Ollama model's (e.g. 1024/4096), and points carry real vectors rather than
random ones.

## Performance caveats

- Embedding real vectors is **much slower** than mock — the first call also
  loads the model into Ollama. Expect seconds-to-minutes depending on model size,
  hardware, and chunk count.
- On Apple Silicon, running Ollama **natively on the host** (option A) uses Metal
  acceleration; Ollama inside a container (option B) may be CPU-only.
- Larger models produce higher-dimensional vectors — more storage and slower
  similarity search in Qdrant.

## Troubleshooting

- **"model not found"** — pull it on the host that actually runs Ollama
  (`ollama pull ...`), and match the provider's model name.
- **Connection refused / timeouts** — almost always the `localhost` vs
  `host.docker.internal` / `ollama` mix-up from Step 2. See
  [../troubleshooting.md](../troubleshooting.md#ollama-not-reachable-from-docker).
