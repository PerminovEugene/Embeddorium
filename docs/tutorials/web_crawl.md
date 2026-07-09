# Tutorial: crawl a website

## Goal

Ingest web pages by crawling — fetch a seed URL, optionally follow links to a
given depth, and run everything through parse → chunk → embed → store. Assumes
the stack is up (see the [first mock run](first_mock_run.md)).

Architecture of the crawl chain:
[../architecture.md](../architecture.md#the-crawl-chain-web).

## Step 1 — Create a Web dataset

In the UI → **Datasets** → **Create** → type **Web**. Fields:

| Field | Meaning |
| ----- | ------- |
| **URL** | The seed page to start from. |
| **Depth** | How many link-hops to follow. `0` = the seed only; `1` = seed + pages it links to; and so on. |
| **Process child links** | Follow links discovered on fetched pages (up to **depth**). Off = single page. |
| **Process cross-domain links** | Allow following links to *other* domains. Off = stay on the seed's origin. |

Over the API:

```sh
curl -s -X POST http://localhost:8000/datasets \
  -H 'Content-Type: application/json' \
  -d '{"name":"my-site","sourceType":"web","url":"https://example.com","processChildLinks":true,"processCrossDomainLinks":false,"depth":1}'
```

Start small — `depth: 0` or `1` — to see the flow before enlarging the crawl.

## Step 2 — Launch the run

**Pipeline runs** → new run → your web dataset + an embedding provider (the
[mock provider](first_mock_run.md#step-4--create-a-mock-provider) is fine to
start). Launch.

## Step 3 — How discovered links flow

The crawl is a loop, gated for safety:

1. **validate_source** — the validation/dedup gate. Normalizes each URL (web
   strategy), skips it if an active target already exists, otherwise queues a
   fetch. Discovered links loop back here carrying the same run id.
2. **fetch_source** — fetches over TLS, sorts failures into transient (retry) vs
   permanent (give up), and **rejects unsupported content types**.
3. **parse_source → chunk_document** — extract text, split into chunks, and
   record any links found.
4. **schedule_discovered_links** — feeds those links back to the frontier
   (subject to depth and the same-origin / cross-domain policy), then marks the
   target processed.

So a page's links only become new fetches if **process child links** is on, the
**depth** budget allows it, and (for other domains) **process cross-domain links**
is on. The **seed** URL is always exempt from the same-origin check.

## Step 4 — Watch it progress and complete

```sh
docker compose logs -f worker-fetch-source
docker compose logs -f worker-validate-source
ls tmp/pipeline_run/<run-id>/                 # per-URL logs + raw/parsed files
```

Each fetched URL gets a `crawl_target` row whose status walks
`queued → fetching → … → processed` (or a terminal `skipped_unsupported`,
`failed_transient`, `failed_permanent`). The run flips to **`completed`** once no
active targets remain **and** every scheduled embed batch finished — then a Qdrant
collection holds the chunk vectors.

## Content-type and safety notes

- **Unsupported content types are rejected** at fetch time — the crawler targets
  parseable text/HTML, not binaries.
- Fetches use **TLS**; insecure connections are only allowed for explicitly
  allowlisted domains.
- **Same-origin by default.** Cross-domain crawling only happens when you opt in
  with *process cross-domain links* — keep it off unless you mean it, or a crawl
  can fan out across the web.
- Be a good citizen: crawl only sites you're allowed to, and keep depth modest.

## Tuning

You can override chunking and the similarity metric per run (see
[../usage.md](../usage.md#start-a-pipeline-run)) to compare how different chunk
sizes affect retrieval on the same crawled content.
