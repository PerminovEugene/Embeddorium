#!/usr/bin/env bash
#
# Wipe all Postgres data (drop & recreate the public schema) and re-run
# migrations so the database is empty but fully provisioned. Requires the
# postgres service to be running.
#
#   scripts/clean-postgres.sh
source "$(dirname "$0")/lib.sh"

log "Dropping all tables in database '$POSTGRES_DB'"
docker compose exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

log "Re-applying migrations"
docker compose run --rm migrate
