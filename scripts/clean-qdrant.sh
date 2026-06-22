#!/usr/bin/env bash
#
# Delete every Qdrant collection (drops all stored vectors). Requires the qdrant
# service to be running with its REST port published to the host.
#
#   scripts/clean-qdrant.sh
source "$(dirname "$0")/lib.sh"

log "Cleaning Qdrant at $QDRANT_HOST_URL"
collections="$(curl -fsS "$QDRANT_HOST_URL/collections" | python3 -c \
  'import sys, json; print("\n".join(c["name"] for c in json.load(sys.stdin)["result"]["collections"]))')"

if [[ -z "${collections//[[:space:]]/}" ]]; then
  echo "No collections found."
  exit 0
fi

while IFS= read -r c; do
  [[ -z "$c" ]] && continue
  echo "  deleting collection $c"
  curl -fsS -X DELETE "$QDRANT_HOST_URL/collections/$c" >/dev/null
done <<< "$collections"
