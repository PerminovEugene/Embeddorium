fix(server): install parse source dependency

Why:
- Ensure the server can discover the parse_source strategy.

What changed:
- Added trafilatura to the server optional dependencies.
- Documented plugin import-time dependencies.

Validation:
- docker compose config --quiet; 20 focused tests passed

Notes:
- Rebuild the server image before recreating the container.
