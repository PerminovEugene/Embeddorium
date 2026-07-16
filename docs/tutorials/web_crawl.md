# Tutorial: crawl a website

## Goal

Ingest web pages by crawling — fetch a seed URL, optionally follow links to a
given depth, and run everything through parse → chunk → embed → store. Assumes
the stack is up (see the [first mock run](first_mock_run.md)).

Architecture of the crawl chain:
[../architecture.md](../architecture.md#the-crawl-chain-web).

## Step 1 — Create a Web dataset

A web dataset is just a name and a **seed URL** — it holds no crawl settings.
Crawl scope (whether to follow links, cross-domain, and how deep) is a
*pipeline-run* setting, not a dataset field (see Step 2).

In the UI → **Datasets** → **Create** → type **Web**, set the seed **URL**. Over
the API:

```sh
curl -s -X POST http://localhost:8000/datasets \
  -H 'Content-Type: application/json' \
  -d '{"name":"my-site","sourceType":"web","url":"https://example.com"}'
```

## Step 2 — Launch the run (and set the crawl scope)

**Pipeline runs** → new run → your web dataset + an embedding provider (the
[mock provider](first_mock_run.md#step-4--create-a-mock-provider) is fine to
start).

Crawl scope lives on the run's `schedule_discovered_links` actor config — the
single source of truth the crawl actually reads. Set it on the run form:

| Setting (`schedule_discovered_links`) | Meaning |
| ------------------------------------- | ------- |
| **Process child links** (`follow_child_links`) | Follow links discovered on fetched pages. Off = single page. This is the gate that is enforced today. |
| **Process cross-domain links** (`follow_cross_domain`) | Allow following links to *other* domains (off = stay on the seed's origin). Recorded but **not yet enforced**. |
| **Depth** (`max_depth`) | How many link-hops to follow. Recorded but **not yet enforced**. |

Start small — child links off, or a shallow depth — to see the flow before
enlarging the crawl. Launch.

## Step 3 — How discovered links flow

The crawl is a loop, gated for safety:

1. **validate_source** — the validation/dedup gate. Normalizes each URL (web
   strategy), skips it if an active target already exists, otherwise queues a
   fetch. Discovered links loop back here carrying the same run id.
2. **fetch_source** — fetches over TLS, sorts failures into transient (retry) vs
   permanent (give up), and **rejects unsupported content types**.
3. **parse_source → chunk_document** — extract text, split into chunks, and
   record any links found.
4. **schedule_discovered_links** — feeds those links back to the frontier (only
   when `follow_child_links` is on), then marks the target processed. The looped
   links re-enter at **validate_source**, which holds each discovered link to the
   seed's origin (the seed itself is exempt).

So a page's links only become new fetches if **process child links** is on and
the link is same-origin with the seed. The `follow_cross_domain` and `max_depth`
knobs are recorded on the run but not yet enforced, so cross-domain links are
currently always dropped at `validate_source`.

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
- **Same-origin only.** Discovered links are held to the seed's origin at
  `validate_source`; the `follow_cross_domain` knob that would loosen this is not
  yet enforced, so a crawl cannot currently fan out across domains.
- Be a good citizen: crawl only sites you're allowed to, and keep `follow_child_links`
  off unless you mean to walk the site.

## Tuning

You can override chunking and the similarity metric per run (see
[../usage.md](../usage.md#start-a-pipeline-run)) to compare how different chunk
sizes affect retrieval on the same crawled content.
