# Configure hybrid search

Hybrid search runs the semantic and BM25 paths at the same `topK` depth and
combines their chunk rankings with RRF. It does not combine their raw scores.

## Request

```sh
curl -sS -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{
    "configuration": {
      "runId": "<run-uuid>",
      "searchMethod": "hybrid",
      "topK": 20
    },
    "source": {
      "inputs": [{"id":"q1","text":"your query"}]
    }
  }'
```

For each query, the server retrieves at most 20 dense candidates and 20 BM25
candidates, fuses both lists with fixed `RRF_K = 60`, and returns at most 20
unique chunks.

`topK` is both the candidate depth for each retrieval half and the final fused
limit. There are no separate dense/sparse depths or user-configurable RRF
constant in the current API.
