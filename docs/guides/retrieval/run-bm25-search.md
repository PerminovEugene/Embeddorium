# Run BM25 search

Keyword search ranks chunk text in PostgreSQL and does not call an embedding
provider or Qdrant.

## UI

On **Search**, select a completed run, choose **Keyword (BM25)**, enter a query,
and submit.

## API

```sh
curl -sS -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{
    "configuration": {
      "runId": "<run-uuid>",
      "searchMethod": "keyword",
      "topK": 10
    },
    "source": {
      "inputs": [{"id":"q1","text":"exact product or legal term"}]
    }
  }'
```

The `pg_textsearch` `<@>` operator returns a negated BM25 score. Results are
ordered ascending in PostgreSQL, so a lower/more-negative raw score is a better
match. This differs from the higher-is-better convention used by Qdrant, RRF,
and rerankers.

If the migration that creates the BM25 extension/index fails, the keyword path
cannot run. Inspect the `migrate` and `postgres` service logs.
