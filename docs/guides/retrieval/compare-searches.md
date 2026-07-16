# Compare searches

Search Lab compares persisted results. Run each configuration from **Search**
first—for example semantic, keyword, hybrid, and hybrid with reranking—using the
same dataset name and query.

## Compare in the UI

1. Open **Search Lab**.
2. Select two or more saved searches. The first selection becomes the
   comparison anchor.
3. Keep the default query constraint for a like-for-like comparison, or enable
   **Allow different inputs**.
4. Switch between **By chunk**, **By document**, and **By rank**.

The table uses result order as rank. Identical chunks are matched primarily by
`chunkId`; when it is missing, the UI falls back to document ID plus chunk
index.

## History API

```sh
curl -sS http://localhost:8000/searches
curl -sS http://localhost:8000/searches/<search-uuid>
```

The list endpoint omits hits; the detail endpoint returns stored ordered
results. Do not compare the magnitude of scores from different methods as if
they shared a scale.
