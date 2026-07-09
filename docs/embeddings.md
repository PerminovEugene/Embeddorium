# Embedding providers

The embed stage (`worker-embed-chunks`) runs in Docker like every other stage.
Which provider it uses comes from the **provider record you select for each
run** — the run stores a snapshot of it, and the worker reads that snapshot.
The `EMBED_PROVIDER` / `OLLAMA_EMBED_*` variables in `.env.docker` are only the
fallback for runs that carry no provider snapshot.

There are three provider types, trading off speed against realism.

## `mock` — fast, meaningless vectors

Returns random vectors of `MOCK_EMBED_DIM` dimensions. It imports neither
`torch` nor `sentence-transformers` and loads no model, so embedding finishes
almost instantly and the container image stays tiny. Use it to exercise the
**whole pipeline end to end** without waiting on a model.

Retrieval results are random, so this verifies the flow, not query quality.

```sh
EMBED_PROVIDER=mock
MOCK_EMBED_DIM=4096   # optional; defaults to the real model's 4096
```

## `ollama` — remote model over HTTP

Calls an Ollama server over HTTP via `OllamaEmbeddings` (from
`langchain-ollama`). The worker container stays light — no `torch`, no
`sentence-transformers`, just thin `httpx`-based clients.

```sh
EMBED_PROVIDER=ollama
OLLAMA_EMBED_MODEL=qwen3-embedding
OLLAMA_EMBED_BASE_URL=http://host.docker.internal:11434   # see below
```

Pull the model once, on whichever host runs Ollama:

```sh
ollama pull qwen3-embedding
```

### Pointing a container at Ollama

`OLLAMA_EMBED_BASE_URL` has to be reachable from **inside** the
`worker-embed-chunks` container. `http://localhost:11434` will not work there —
each container has its own loopback, separate from the host's.

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

**Ollama in your own container.** If you run Ollama in Docker yourself, attach
it to this project's Compose network and use its container name as the host in
`OLLAMA_EMBED_BASE_URL` (e.g. `http://ollama:11434`).

## `huggingface` — real local model

Embedding with `Qwen/Qwen3-Embedding-8B` via `sentence-transformers` is heavy: a
multi-GB `torch` install and slow inference. It is **not** in the Compose image.
To use it, install the `embedding` extra, leave `EMBED_PROVIDER` unset (or set it
to `huggingface`), and run the actor on the host:

```sh
pip install -e ".[embedding]"
dramatiq backend.actors.embed_chunks_actor --processes 1 --threads 1
```
