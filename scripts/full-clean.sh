#!/usr/bin/env bash
#
# Full reset of the local stack. Runs every maintenance script in order:
#   1. ensure infra (postgres/rabbitmq/qdrant) is up
#   2. stop workers so nothing republishes while we clean
#   3. purge all RabbitMQ messages       (purge-queues.sh)
#   4. drop all Qdrant collections       (clean-qdrant.sh)
#   5. wipe Postgres + re-run migrations  (clean-postgres.sh)
#   6. remove per-URL log dir contents    ($LOG_DIR)
#   7. stop/rm/rebuild/up workers         (rebuild-workers.sh)
#
#   scripts/full-clean.sh
source "$(dirname "$0")/lib.sh"

log "FULL CLEAN starting"

log "Ensuring infrastructure is up"
docker compose up -d postgres rabbitmq qdrant

log "Stopping workers"
docker compose stop "${WORKERS[@]}" 2>/dev/null || true

"$SCRIPTS_DIR/purge-queues.sh"
"$SCRIPTS_DIR/clean-qdrant.sh"
"$SCRIPTS_DIR/clean-postgres.sh"

log "Removing log directory contents ($LOG_DIR)"
if [[ -d "$LOG_DIR" ]]; then
  rm -rf "${LOG_DIR:?}"/*
fi

"$SCRIPTS_DIR/rebuild-workers.sh"

log "FULL CLEAN done"
