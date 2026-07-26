#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Error: the shared virtual environment is missing. Run ./scripts/linux/setup.sh first."
  exit 1
fi

echo "Starting the Libra Assist admin console..."
echo "Frontend: http://localhost:7800"
echo

cd "$PROJECT_ROOT"
exec "$PYTHON_BIN" -m uvicorn app.main:app \
  --app-dir "$PROJECT_ROOT/code/frontend-admin" \
  --host 127.0.0.1 \
  --port 7800 \
  --reload
