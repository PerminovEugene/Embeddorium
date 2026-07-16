# Error handling

## API requests

FastAPI schemas reject invalid top-level request shapes. Service code returns
explicit 400/404/409 errors for invalid provider/run settings, unknown records,
and launching an already-running run.

One exception is generic actor configuration during run creation: if Pydantic
validation of an actor block fails, the server logs the malformed input and
uses all defaults for that block rather than rejecting the request.

## Actor retries

Every Dramatiq actor declares `max_retries=3`. A handler raises for conditions
classified as transient, including connection/timeouts during web fetch and
missing rows that may reflect ordering/visibility. Dramatiq's default retry
middleware supplies backoff.

Permanent conditions update the target and return:

- Unsupported MIME/parser: `skipped_unsupported`
- Keyword mismatch: `skipped` with `not_relevant`
- Permanent fetch error: `failed_permanent`
- Transient fetch before retry: `failed_transient`

There is no custom dead-letter consumer. Exhausted messages remain diagnosable
through RabbitMQ, target state, and worker logs.

## Idempotency

- Actors claim expected target statuses with compare-and-set updates.
- Outbox `dedup_key` is unique.
- Fetches, documents, chunks, and discovered links use stable/natural-key
  update logic.
- Qdrant point IDs are chunk UUIDs.
- Run completion uses a conditional update from `running` to `completed`.

Delivery is at-least-once. The two direct broker handoffs at launch and after
target creation do not have the atomic guarantee of outbox-backed stages.

## Retrieval degradation

Rerank endpoint failures return the original hybrid order. Search-history
write failures do not fail a search. Other embedding, Qdrant, or PostgreSQL
search failures are not converted into fallback results.
