#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/code/frontend-admin/docker/compose.yml"

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "Error: Docker is not installed or the Docker engine is not running."
  exit 1
fi

echo "Starting the Libra Assist admin console..."
echo "Frontend: http://localhost:7800"
echo

exec docker compose -f "$COMPOSE_FILE" up --build
