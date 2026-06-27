#!/usr/bin/env bash
#
# Seed the local-file (XML) ingestion chain from a sources config, inside the
# docker-compose network (uses .env.docker, so it reaches rabbitmq/postgres
# by service name).
#
# Usage:
#   scripts/seed_files.sh [config.files.json]
#
# The config path is relative to the repo root (mounted at /app in the
# container). Defaults to config.files.json. The file-chain workers + outbox
# dispatcher should be up:
#   docker compose up -d
set -euo pipefail

CONFIG="${1:-config.files.json}"

docker compose run --rm seed-files "$CONFIG"
