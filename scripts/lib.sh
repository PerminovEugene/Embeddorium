# Shared helpers for the maintenance scripts. Source this; do not run directly.
#
#   source "$(dirname "$0")/lib.sh"
#
# Provides: REPO_ROOT, SCRIPTS_DIR, WORKERS, QDRANT_HOST_URL, log(), and loads
# the docker env file (.env.docker) so POSTGRES_*/RABBITMQ_*/QDRANT_* are set.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$REPO_ROOT/scripts"
cd "$REPO_ROOT"

ENV_FILE="${ENV_FILE:-.env.docker}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# The pipeline workers (everything started by `docker compose up` except infra).
WORKERS=(
  worker-crawl-frontier-manager
  worker-fetch-source
  worker-parse-source
  worker-chunk-document
  worker-schedule-embeddings
  worker-schedule-links
  worker-outbox-dispatcher
)

# Qdrant's REST API, reached from the host (container port 6333 is published).
QDRANT_HOST_URL="${QDRANT_HOST_URL:-http://localhost:6333}"

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
