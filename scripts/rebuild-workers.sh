#!/usr/bin/env bash
#
# Stop, remove, and rebuild the pipeline workers, then bring them back up.
# Bringing them up pulls in the `migrate` dependency, so schema is applied first.
#
#   scripts/rebuild-workers.sh
source "$(dirname "$0")/lib.sh"

log "Stopping workers"
docker compose stop "${WORKERS[@]}"

log "Removing worker containers"
docker compose rm -f "${WORKERS[@]}"

log "Rebuilding worker images"
docker compose build "${WORKERS[@]}"

log "Starting workers"
docker compose up -d "${WORKERS[@]}"
