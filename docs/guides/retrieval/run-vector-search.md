# Run vector search

Vector search is the `semantic` search method. It requires a completed run with
an embedding provider that is still reachable from the API container.

## UI

On **Search**, select **Select pipeline results**, choose the run, set the
method to **Semantic (vector)**, enter a query, choose Top K, and submit.

## API

```sh
curl -sS -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{
    "configuration": {
      "runId": "<run-uuid>",
      "searchMethod": "semantic",
      "topK": 10
    },
    "source": {
      "inputs": [{"id":"q1","text":"your query"}]
    }
  }'
```

The server embeds the query with the run's saved provider, searches its saved
collection, and filters points whose `pipeline_run_id` equals the run UUID.
Result scores are Qdrant scores for the collection's configured distance.

Do not use a mock-backed run to judge relevance: mock query and chunk vectors
are random.
