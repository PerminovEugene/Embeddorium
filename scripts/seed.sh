#!/usr/bin/env bash
#
# Seed the crawl frontier from a sources config, inside the docker-compose
# network (uses .env.docker, so it reaches rabbitmq/postgres by service name).
#
# Usage:
#   scripts/seed.sh [config.json]
#
# The config path is relative to the repo root (mounted at /app in the container).
# Defaults to config.json. The pipeline workers + outbox dispatcher should be up:
#   docker compose up -d
set -euo pipefail

CONFIG="${1:-config.json}"

docker compose run --rm seed "$CONFIG"
