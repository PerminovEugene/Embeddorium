# Embedding providers

The embed stage (`worker-embed-chunks`) runs in Docker like every other stage.
Which provider it uses is set by `EMBED_PROVIDER` in `.env.docker`. There are
three, trading off speed against realism.

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

**Ollama as a Compose service.** The `docker-compose.yml` defines an optional
`ollama` service (profile `ollama`, not started by a plain `docker compose up`).
Start it and use the service name as the host:

```sh
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull qwen3-embedding
```

```sh
# .env.docker
OLLAMA_EMBED_BASE_URL=http://ollama:11434
```

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

## `huggingface` — real local model

Embedding with `Qwen/Qwen3-Embedding-8B` via `sentence-transformers` is heavy: a
multi-GB `torch` install and slow inference. It is **not** in the Compose image.
To use it, install the `embedding` extra, leave `EMBED_PROVIDER` unset (or set it
to `huggingface`), and run the actor on the host:

```sh
pip install -e ".[embedding]"
dramatiq backend.actors.embed_chunks_actor --processes 1 --threads 1
```
