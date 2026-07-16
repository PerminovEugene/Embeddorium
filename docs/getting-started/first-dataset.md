# Create your first dataset

A dataset describes source locations. It does not contain parser, chunker,
provider, crawl-depth, or search settings; those belong to a pipeline run.

## Web dataset

In **Datasets**, create a record with:

- `name`: a display name
- `sourceType`: `web`
- `url`: one seed URL

API example:

```sh
curl -sS -X POST http://localhost:8000/datasets \
  -H 'Content-Type: application/json' \
  -d '{"name":"example","sourceType":"web","url":"https://example.com"}'
```

If the URL has no `http://` or `https://` scheme, the launch seeder prepends
`https://`.

## Local XML dataset

Put XML files under the repository's `sources/` directory. Select a file or
folder using the UI source browser; stored paths are relative to that root.

```sh
curl -sS -X POST http://localhost:8000/datasets \
  -H 'Content-Type: application/json' \
  -d '{"name":"local-laws","sourceType":"local","paths":["xml.2026.en"]}'
```

A directory is searched recursively for `*.xml`. An individual path with a
suffix is queued directly and then validated for existence and readability.
The browser rejects traversal outside the source root. Absolute paths are
accepted by the API seeder for administrative use, but Compose workers can read
only paths visible inside their containers.

## Dataset operations

The API supports list, create, fetch, replace, and delete at `/datasets`.
Pipeline runs keep a dataset snapshot, so changing the dataset later does not
change an existing run.
