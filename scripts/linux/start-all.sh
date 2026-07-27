#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BACKEND_COMPOSE_FILE="$PROJECT_ROOT/code/backend/docker/compose.yml"
FRONTEND_COMPOSE_FILE="$PROJECT_ROOT/code/frontend-admin/docker/compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"
SECRET_FILE="$PROJECT_ROOT/.credentials"

# Shared Docker migration helpers.
source "$SCRIPT_DIR/docker-utils.sh"

BACKEND_COMPOSE_COMMAND=(
  docker compose
  --env-file "$SECRET_FILE"
  --env-file "$ENV_FILE"
  -f "$BACKEND_COMPOSE_FILE"
)
FRONTEND_COMPOSE_COMMAND=(docker compose -f "$FRONTEND_COMPOSE_FILE")

if [[ ! -f "$ENV_FILE" || ! -f "$SECRET_FILE" ]]; then
  echo "Error: .env or .credentials is missing. Run ./scripts/linux/setup.sh first."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "Error: Docker is not installed or the Docker engine is not running."
  exit 1
fi

remove_legacy_backend_containers

cleanup() {
  echo
  echo "Stopping frontend and backend containers..."
  "${FRONTEND_COMPOSE_COMMAND[@]}" down
  "${BACKEND_COMPOSE_COMMAND[@]}" down
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "Starting backend containers..."
"${BACKEND_COMPOSE_COMMAND[@]}" up -d --build

echo "Starting the admin frontend container..."
"${FRONTEND_COMPOSE_COMMAND[@]}" up -d --build

echo
echo "Services:"
echo "  Frontend: http://localhost:7800"
echo "  API:      http://localhost:7799"
echo "  Swagger:  http://localhost:7799/docs"
echo "  Qdrant:   http://localhost:7833/dashboard"
echo
echo "Press Ctrl+C to stop all services."
echo

"${FRONTEND_COMPOSE_COMMAND[@]}" logs -f admin
