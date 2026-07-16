# Security

Embeddorium is configured as a trusted local development system, not a hardened
deployment.

## Current controls

- Web fetch TLS verification is on by default. A run can disable it, and
  `INSECURE_TLS_DOMAINS` can allowlist domains for insecure TLS.
- Web source responses are limited to 10 MiB and supported text/XML MIME types.
- Discovered web links are restricted to the parent document's origin.
- The source browser resolves paths under `SOURCE_ROOT` and rejects traversal.
- SQL BM25 queries bind query text and pipeline IDs as parameters.
- Provider API keys are accepted as config and sent as bearer credentials to
  compatible endpoints.

## Known exposure

- FastAPI has no authentication or authorization.
- CORS allows credentials for localhost UI origins on ports 5173–5175.
- Qdrant, Postgres, RabbitMQ, RabbitMQ management, API, and UI ports are
  published to the host by Compose.
- `.env.example` and `.env.docker` contain development credentials. They must
  not be treated as production secrets.
- Provider configuration, including API keys, is stored in PostgreSQL JSON and
  returned by provider GET endpoints; the UI can read it.
- Local dataset APIs accept absolute paths for administrative use. The browse
  endpoint is root-confined, but the seeder deliberately passes absolute paths
  through.
- There is no request rate limiting, audit-log policy, secret redaction
  contract, network policy, encryption-at-rest setup, or CSRF protection layer.

Do not expose the default Compose stack to an untrusted network. A production
threat model and hardening guide are not present: {MISSED_INFO}
