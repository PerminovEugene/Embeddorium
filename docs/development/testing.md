# Testing

## Backend suite

```sh
.venv/bin/python -m pytest backend/tests -q
```

Run a focused file while iterating:

```sh
.venv/bin/python -m pytest \
  backend/tests/server/test_search_strategy.py -v
```

The suite contains actor handler tests, plugin discovery/behavior tests, client
tests, outbox tests, server route/service tests, and storage tests. Most actor
tests inject stores/clients rather than requiring RabbitMQ.

## Static checks

```sh
ruff check .
ruff format --check .
cd ui && npm run lint && npm run build
```

## Flow validation

For changes spanning actors, storage, queues, providers, or retrieval:

1. Start the Compose stack.
2. Create a mock embedding provider.
3. Ingest a bounded dataset with child links disabled.
4. Confirm the run completes and chunk statuses become `embedded`.
5. Run keyword search and, where relevant, semantic/hybrid search.
6. Inspect target errors and raw/parsed artifacts.

The mock provider avoids a model-service dependency but cannot validate
semantic relevance. A real provider is needed for relevance-sensitive changes.

The repository contains no configured CI workflow: {MISSED_INFO}
