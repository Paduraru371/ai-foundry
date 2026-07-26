#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/code/backend/docker/compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"
SECRET_FILE="$PROJECT_ROOT/.credentials"

# Shared Docker migration helpers.
source "$SCRIPT_DIR/docker-utils.sh"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: Docker is not installed or is not available in PATH."
  exit 1
fi

if [[ ! -f "$ENV_FILE" || ! -f "$SECRET_FILE" ]]; then
  echo "Error: .env or .credentials is missing. Run ./scripts/linux/setup.sh first."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker is installed, but the Docker engine is not running."
  exit 1
fi

remove_legacy_backend_containers

echo "Starting the RAG API and Qdrant with Docker Compose..."
echo "API:     http://localhost:7799"
echo "Swagger: http://localhost:7799/docs"
echo "Qdrant:  http://localhost:7833/dashboard"
echo

cd "$PROJECT_ROOT"
exec docker compose \
  --env-file "$SECRET_FILE" \
  --env-file "$ENV_FILE" \
  -f "$COMPOSE_FILE" \
  up --build
