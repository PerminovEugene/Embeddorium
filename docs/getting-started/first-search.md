# Run your first search

Searches select a completed pipeline run. The server reads the collection and
embedding provider from that run rather than accepting an arbitrary model from
the request.

## Search from the UI

1. Open **Search**.
2. Select **Select pipeline results**.
3. Choose a completed run.
4. Enter one or more query texts.
5. Choose **Semantic**, **Keyword**, or **Hybrid** and a positive Top K.
6. Submit.

Each query is persisted separately with its ordered results. Open **Search Lab**
to compare saved searches over the same dataset.

## Search through the API

```sh
curl -sS -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{
    "configuration": {
      "runId": "<completed-run-uuid>",
      "searchMethod": "keyword",
      "topK": 10
    },
    "source": {
      "inputs": [
        {"id": "q1", "text": "What is the applicable tax rate?"}
      ]
    }
  }'
```

Use `semantic` for dense Qdrant search or `hybrid` for dense plus BM25 RRF.
`embedding` remains accepted as a legacy alias for `semantic`.

The response is `{"status":"success","results":[...]}`. Hits include the
query ID/text, score, chunk/document IDs, chunk index/text, dataset name,
source URL, and chunk metadata.
