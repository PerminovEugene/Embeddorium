# Project Architecture

A distributed crawler and indexer for legal web sources. Seed URLs come from a config file; the system crawls them, chunks the text, generates vector embeddings, and stores everything for later retrieval.

---

## Entry point

`laws_agent/runners/add_web_source_job.py <config.json>`

Reads the config, iterates over groups (e.g. "Estonia") and their source URLs, and pushes each `(group, url)` pair into the first queue. Nothing else — it just seeds the pipeline.

**config.json shape:**
```json
{
  "groups": [
    {
      "name": "Estonia",
      "sources": [{ "link": "emta.ee", "description": "..." }]
    }
  ]
}
```

---

## Pipeline (three queues, three workers)

```
add_web_source_job
       │
       ▼
laws.crawl.link.process.v1
       │
       ▼
link_processor_actor          ← deduplication gate
       │ (new URLs only)
       ▼
laws.crawl.source.fetch.v1
       │
       ▼
web_source_processor_actor    ← fetch → parse → chunk → save
       │                  │
       │                  └──► laws.crawl.link.process.v1
       │                        (discovered links, looped back)
       ▼
laws.embed.chunk.generate.v1
       │
       ▼
embed_chunks_actor            ← embed → save to Qdrant
```

### link_processor_actor

Receives a URL and group. Normalises the URL, checks `crawl_targets` in Postgres — if a non-failed record already exists, skips it. Otherwise creates a `crawl_target` row (status `queued`) and pushes its ID to the fetch queue. Also enforces same-origin policy for links discovered during crawling (seed URLs bypass this).

### web_source_processor_actor

Receives a `crawl_target_id`. Fetches the URL with `requests`, extracts main text with `trafilatura`, splits into ~1200-token chunks with `langchain MarkdownTextSplitter`. Saves a `Document` and its `DocumentChunk` rows to Postgres, updates the crawl target status to `processed`. For each batch of chunks: enqueues to the embed queue. For each link found in a chunk: loops it back through the link processor queue (so crawling fans out depth-first).

### embed_chunks_actor

Receives chunk IDs. Loads them from Postgres, runs `Qwen/Qwen3-Embedding-8B` via `sentence-transformers` to produce normalised vectors, upserts them into a Qdrant collection named `LAWS_{group}_qwen_embed_8b`.

---

## Storage

| Store    | What lives there                                      |
|----------|-------------------------------------------------------|
| Postgres | `documents`, `document_chunks`, `crawl_targets`       |
| Qdrant   | Vector embeddings with `chunk_id` / `document_id` payload |

`crawl_targets` is the crawl frontier: every URL the system has seen gets a row with a status (`queued → processing → processed / failed / skipped`). This is what prevents re-crawling.

---

## Infrastructure (docker-compose)

| Service                    | Role                              |
|----------------------------|-----------------------------------|
| `postgres`                 | Relational store                  |
| `qdrant`                   | Vector store                      |
| `rabbitmq`                 | Message broker (+ management UI)  |
| `worker-link-processor`    | Runs link_processor_actor         |
| `worker-web-source-processor` | Runs web_source_processor_actor |
| `worker-embed-chunks`      | Runs embed_chunks_actor           |

Workers are built from `Dockerfile.dev`, mount the source tree as a volume, and use `dramatiq --watch laws_agent` so they reload on any code change.
