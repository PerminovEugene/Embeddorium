#!/usr/bin/env bash
#
# Purge all messages from every RabbitMQ queue (the queues themselves are kept).
# Requires the rabbitmq service to be running.
#
#   scripts/purge-queues.sh
source "$(dirname "$0")/lib.sh"

VHOST="${RABBITMQ_VHOST:-/}"

log "Purging all RabbitMQ queues in vhost '$VHOST'"
queues="$(docker compose exec -T rabbitmq \
  rabbitmqctl list_queues -p "$VHOST" name --quiet --no-table-headers)"

if [[ -z "${queues//[[:space:]]/}" ]]; then
  echo "No queues found."
  exit 0
fi

while IFS= read -r q; do
  [[ -z "$q" ]] && continue
  echo "  purging $q"
  docker compose exec -T rabbitmq rabbitmqctl purge_queue -p "$VHOST" "$q"
done <<< "$queues"
