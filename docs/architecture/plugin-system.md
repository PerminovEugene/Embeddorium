# Plugin system

The plugin system is import-time discovery plus small strategy contracts. It
does not load external packages from a marketplace or execute plugins in a
sandbox.

## Discovery

Actor registries walk the corresponding package below `backend/plugins`, skip
framework and underscore-prefixed modules, import candidates, and collect
concrete subclasses with a named class-level config. Provider discovery also
associates each `ModelTypeHandler` with the provider package containing it.

An import failure logs a warning and skips that module. Duplicate strategy names
keep the first class discovered and log a warning. Registries cache results for
the process lifetime.

## Responsibility split

Actor handlers own database state, file I/O, outbox messages, status changes,
and shared validation. Strategies own the varying transformation:

- source identity and admissibility
- fetching source bytes/text
- relevance decisions
- parsing by format
- chunk construction
- provider/model target resolution

This keeps most strategies directly unit-testable without RabbitMQ or Postgres.

## Configuration metadata

`FieldSpec` supports text, number, checkbox, select, and provider-ID controls,
with defaults, bounds, options, placeholder, and required state. Provider config
values receive server-side type/bound validation. Generic actor settings are
validated through Pydantic models when a run is created; malformed blocks are
logged and replaced with the entire model default.

The frontend currently exposes a selectable strategy for chunkers. For other
actors it chooses the built-in strategy by dataset type or fixed actor mapping,
even if discovery returns more strategies. Extending those selectors requires a
frontend change.
