# Contributing

Embeddorium is licensed under Apache-2.0. Issues and pull requests are welcome.

## Before changing code

1. Read [Repository structure](development/repository-structure.md).
2. Create a Python 3.11+ environment as described in
   [Development setup](development/setup.md).
3. Keep provider selection and pipeline settings run-scoped; do not introduce a
   mutable global choice where a run snapshot already exists.
4. Add a SQL migration for persisted schema changes; do not rewrite a deployed
   migration unless the deployment policy explicitly permits it.

## Validate a contribution

```sh
.venv/bin/python -m pytest backend/tests -q
ruff check .
ruff format --check .
cd ui && npm run lint && npm run build
```

Run the affected ingestion or retrieval flow with a `mock` provider when the
change crosses service boundaries. See [Testing](development/testing.md).

## Pull requests

Describe why the change is needed, the user-visible behavior, and the checks
you ran. Preserve unrelated working-tree changes and do not include local data,
environment files, `tmp/`, or `.codex/commit-context.md`.

The repository does not define a code of conduct, issue template, pull-request
template, or maintainer review policy: {MISSED_INFO}
