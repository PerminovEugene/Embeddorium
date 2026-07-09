# Tutorial: import local XML files

## Goal

Ingest a folder of local `*.xml` files (instead of crawling the web) and run them
through the same parse → chunk → embed → store pipeline. Assumes the stack is up
(see the [first mock run](first_mock_run.md)).

The file chain reads a local dump, optionally filters files by keyword, and
rejoins the shared pipeline at `parse_source`. Architecture:
[../architecture.md](../architecture.md#the-file-chain-local-xml).

## Step 1 — Put files under the source root

Local files must live in the repo's **`sources/`** directory. It's bind-mounted
into the services that need it — the validation and fetch workers and the API —
at `/app/sources`:

| Service | Host path | Container path |
| ------- | --------- | -------------- |
| `worker-validate-source` | `./sources` | `/app/sources` |
| `worker-fetch-source` | `./sources` | `/app/sources` |
| `server` | `./sources` | `/app/sources` |

`sources/` is gitignored. Drop your XML in there, e.g.:

```sh
mkdir -p sources/my-dump
cp /path/to/*.xml sources/my-dump/
```

No container restart is needed — it's a live bind mount. Only files **inside**
`sources/` are reachable; paths that escape the root are rejected.

## Step 2 — Create a Local dataset

A **Local** dataset points at paths **relative to the source root**. In the UI →
**Datasets** → **Create** → type **Local**, then pick your folder or files with
the source browser (it lists what's under `sources/`). For `sources/my-dump`,
the stored path is `my-dump`.

Over the API the body is:

```sh
curl -s -X POST http://localhost:8000/datasets \
  -H 'Content-Type: application/json' \
  -d '{"name":"my-xml","sourceType":"local","paths":["my-dump"]}'
```

- **Paths** may be folders or individual files. A **folder** is enumerated
  recursively for `*.xml` (the default glob); each match becomes one seed
  message. An entry that resolves to no real file is silently skipped.

## Step 3 — Launch the run

**Pipeline runs** → new run → your local dataset + an embedding provider (the
[mock provider](first_mock_run.md#step-4--create-a-mock-provider) is fine for a
first pass). Launch it.

Internally the server publishes **one `validate_source` message per file**. Each
file is validated (exists + readable), read by `fetch_source`'s local-file
strategy, stored as a `SourceFetch`, optionally keyword-filtered
(`filter_documents`), then parsed, chunked, embedded, and stored — identical to
the crawl path from `parse_source` onward.

## Step 4 — Watch artifacts appear

As with any run, artifacts land on the host under the run directory:

```sh
ls tmp/pipeline_run/<run-id>/sources/<source-id>/raw/     # the raw XML
ls tmp/pipeline_run/<run-id>/sources/<source-id>/parsed/  # extracted text
```

The run reaches **`completed`**, and a Qdrant collection holds the chunk vectors
(http://localhost:6333/dashboard).

## About keyword filtering

The `filter_documents` stage pulls each document's title from the XML and checks
it against a configurable keyword list. **With no keywords configured, everything
passes.** Non-matches are marked `skipped` (`skip_reason="not_relevant"`) and go
no further — expected behavior, not an error. Details in
[../architecture.md](../architecture.md#the-file-chain-local-xml).

## Notes

- `schedule_discovered_links` finds zero links in an XML document — that's
  expected; the file chain doesn't follow links.
- To point the actors at a different host directory, override `SOURCE_ROOT` and
  adjust the bind mount in `docker-compose.yml` accordingly.
