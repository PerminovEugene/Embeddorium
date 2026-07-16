# Run your first ingestion

Before creating a run, create a dataset and an `embedding` provider. Run
creation and launch are separate operations.

## Create a pending run

Replace the two UUIDs below. Plugin field keys inside actor settings use the
keys published by `GET /actor-configs`; chunker settings are nested under
`chunk_document.settings`.

```sh
curl -sS -X POST http://localhost:8000/pipeline-runs \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "example-markdown",
    "datasetId": "<dataset-uuid>",
    "actorSettings": {
      "embed_chunks": {
        "provider": "<embedding-provider-uuid>",
        "similarity": "cosine"
      },
      "chunk_document": {
        "chunker": "text_markdown",
        "settings": {
          "chunk_size": 1200,
          "chunk_overlap": 150
        }
      },
      "schedule_discovered_links": {
        "followChildLinks": false
      }
    }
  }'
```

The response status is `pending`. The server has already copied the dataset and
provider into the run snapshot.

## Launch it

```sh
curl -sS -X POST \
  http://localhost:8000/pipeline-runs/<run-uuid>/launch
```

The server publishes one web seed or one message per matched local XML file,
sets `startedAt`, clears an earlier `finishedAt`, and changes the run to
`running`. Launching a currently running run returns HTTP 409; pending, failed,
and completed runs may be launched.

## Monitor it

```sh
curl -sS http://localhost:8000/pipeline-runs/<run-uuid>
curl -sS 'http://localhost:8000/pipeline-runs/<run-uuid>/targets?limit=50&offset=0'
```

The run completes when no active targets remain and the number of completed
embedding batches reaches the number scheduled. Target failures remain visible
even when the run reaches `completed`.
