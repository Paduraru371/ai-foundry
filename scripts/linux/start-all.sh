#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/code/backend/docker/compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"
SECRET_FILE="$PROJECT_ROOT/.credentials"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"

# Shared Docker migration helpers.
source "$SCRIPT_DIR/docker-utils.sh"

COMPOSE_COMMAND=(
  docker compose
  --env-file "$SECRET_FILE"
  --env-file "$ENV_FILE"
  -f "$COMPOSE_FILE"
)

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Error: the shared virtual environment is missing. Run ./scripts/linux/setup.sh first."
  exit 1
fi

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
  echo "Stopping backend containers..."
  "${COMPOSE_COMMAND[@]}" down
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "Starting backend containers..."
"${COMPOSE_COMMAND[@]}" up -d --build

echo
echo "Services:"
echo "  Frontend: http://localhost:7800"
echo "  API:      http://localhost:7799"
echo "  Swagger:  http://localhost:7799/docs"
echo "  Qdrant:   http://localhost:7833/dashboard"
echo
echo "Press Ctrl+C to stop all services."
echo

cd "$PROJECT_ROOT"
"$PYTHON_BIN" -m uvicorn app.main:app \
  --app-dir "$PROJECT_ROOT/code/frontend-admin" \
  --host 127.0.0.1 \
  --port 7800 \
  --reload
