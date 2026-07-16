# Configure reranking

Reranking is an optional second stage for hybrid search. The backend expects an
HTTP service with a Jina/Cohere-style rerank contract: the request contains
`model`, `query`, and `documents`; each response result contains `index` and
either `relevance_score` or `score`.

## 1. Create a cross-encoder provider

The built-in cross-encoder capability is registered under the `ollama`
provider type, although the URL may point to vLLM, Infinity, TEI, or another
compatible rerank server.

```sh
curl -sS -X POST http://localhost:8000/providers \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "local-reranker",
    "providerType": "ollama",
    "modelType": "cross-encoder",
    "config": {
      "url": "http://host.docker.internal",
      "port": 8001,
      "model_name": "<served-model-name>",
      "rerank_path": "v1/rerank"
    }
  }'
```

Use `rerank` instead of `v1/rerank` when that is the route exposed by your
server.

## 2. Enable reranking on hybrid search

```sh
curl -sS -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{
    "configuration": {
      "runId": "<run-uuid>",
      "searchMethod": "hybrid",
      "topK": 30,
      "useReranking": true,
      "rerankerProviderId": "<cross-encoder-provider-uuid>",
      "rerankerTopK": 5
    },
    "source": {
      "inputs": [{"id":"q1","text":"your query"}]
    }
  }'
```

The provider ID and positive `rerankerTopK` are required. Runtime rerank
failures fall back to the first five hybrid results; invalid provider IDs or a
non-cross-encoder provider return HTTP 400.
