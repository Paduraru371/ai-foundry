#!/usr/bin/env bash
# The teaching lane: the API on your machine, Qdrant and the console in Docker.
#
# Usage:
#   ./dev.sh
#   ./dev.sh --port 7801
#   ./dev.sh --bind-all
#   ./dev.sh --skip-docker
#   ./dev.sh --force
#
# The API runs in the repository virtual environment. Qdrant and the selected
# frontend run in Docker. Azure CLI is required only for Azure identity-based
# configurations.
set -euo pipefail

PORT=7799
# The frontend runs in Docker and reaches the host through the Docker bridge.
# On Linux the API must listen beyond loopback for that connection to work.
BIND_ALL=1
SKIP_DOCKER=0
NO_RELOAD=0
FORCE=0
FRONTEND=frontend

usage() {
  cat <<'EOF'
Usage: ./scripts/dev.sh [options]

Options:
  --port PORT                 API port (default: 7799)
  --bind-all                  Bind the API to 0.0.0.0 (default on Linux)
  --loopback                  Bind only to 127.0.0.1
  --skip-docker               Do not start the Docker services
  --no-reload                 Disable uvicorn auto-reload
  --force                     Stop an orphaned uvicorn server holding the port
  --frontend NAME             frontend or frontend-admin
  -h, --help                  Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --port)
      [ "$#" -ge 2 ] || { echo "Missing value for --port." >&2; exit 1; }
      PORT=$2
      shift 2
      ;;
    --bind-all)
      BIND_ALL=1
      shift
      ;;
    --loopback)
      BIND_ALL=0
      shift
      ;;
    --skip-docker)
      SKIP_DOCKER=1
      shift
      ;;
    --no-reload)
      NO_RELOAD=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --frontend)
      [ "$#" -ge 2 ] || { echo "Missing value for --frontend." >&2; exit 1; }
      FRONTEND=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$PORT" in
  ''|*[!0-9]*) echo "Port must be a number." >&2; exit 1 ;;
esac
if [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
  echo "Port must be between 1 and 65535." >&2
  exit 1
fi
case "$FRONTEND" in
  frontend|frontend-admin) ;;
  *) echo "--frontend must be frontend or frontend-admin." >&2; exit 1 ;;
esac

step() {
  printf '\n\033[36m[%s] %s\033[0m\n' "$1" "$2"
}

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
cd "$PROJECT_ROOT"

step 0 "Python dependencies"
if [ ! -x .venv/bin/python ]; then
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
  elif command -v python >/dev/null 2>&1; then
    python -m venv .venv
  else
    echo "Python 3.11+ was not found." >&2
    exit 1
  fi
fi
.venv/bin/python -m pip install -r requirements.txt --disable-pip-version-check \
  || { echo "Project dependencies could not be installed." >&2; exit 1; }

step 1 "Configuration"
if [ ! -f .env ]; then
  echo "No .env here. Start from: cp .env.example .env" >&2
  exit 1
fi

USES_AZURE=0
USES_IDENTITY=0
grep -qE '^(LLM_PROVIDER|EMBEDDING_PROVIDER)=azure[[:space:]]*$|^AGENT_MODE=foundry[[:space:]]*$' .env \
  && USES_AZURE=1
grep -qE '^AZURE_AI_AUTH=identity[[:space:]]*$' .env && USES_IDENTITY=1
printf '\033[32m    configuration loaded from %s/.env\033[0m\n' "$PROJECT_ROOT"

QDRANT_URL=$(sed -n 's/^QDRANT_URL=//p' .env | tail -n 1)
if [ -n "$QDRANT_URL" ] && [[ "$QDRANT_URL" != *localhost* ]]; then
  printf '\033[33m    QDRANT_URL=%s - expected localhost here; the API is NOT in the compose network\033[0m\n' "$QDRANT_URL"
fi

step 2 "Azure identity"
if [ "$USES_AZURE" -eq 1 ] && [ "$USES_IDENTITY" -eq 1 ]; then
  if ! command -v az >/dev/null 2>&1; then
    echo "az not found. Install it: https://learn.microsoft.com/cli/azure/install-azure-cli" >&2
    exit 1
  fi
  if ! ACCOUNT=$(az account show --query '[user.name,name]' -o tsv 2>/dev/null); then
    echo "Not signed in. Run: az login" >&2
    exit 1
  fi
  printf '\033[32m    %s\033[0m\n' "$ACCOUNT"
else
  echo "    not required for the selected local/key-based configuration"
fi

port_is_busy() {
  .venv/bin/python - "$PORT" <<'PY'
import socket
import sys

sock = socket.socket()
try:
    sock.bind(("0.0.0.0", int(sys.argv[1])))
except OSError:
    raise SystemExit(0)
finally:
    sock.close()
raise SystemExit(1)
PY
}

port_pids() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true
  elif command -v fuser >/dev/null 2>&1; then
    fuser -n tcp "$PORT" 2>/dev/null | tr ' ' '\n' | sed '/^$/d'
  fi
}

step 3 "Port $PORT"
if port_is_busy; then
  ORPHANS=()
  while IFS= read -r PID; do
    [ -n "$PID" ] || continue
    COMMAND_LINE=$(tr '\0' ' ' <"/proc/$PID/cmdline" 2>/dev/null || true)
    if [[ "$COMMAND_LINE" =~ uvicorn|multiprocessing\.spawn ]]; then
      ORPHANS+=("$PID")
    fi
  done < <(port_pids)

  if [ "${#ORPHANS[@]}" -gt 0 ] && [ "$FORCE" -eq 1 ]; then
    for PID in "${ORPHANS[@]}"; do
      printf '\033[33m    stopping orphaned server %s\033[0m\n' "$PID"
      kill "$PID" 2>/dev/null || true
    done
    for _ in 1 2 3; do
      port_is_busy || break
      sleep 1
    done
  fi

  if port_is_busy; then
    printf '\033[33m    in use.\033[0m\n'
    if [ "${#ORPHANS[@]}" -gt 0 ]; then
      printf '\033[33m    an orphaned local server is holding it - re-run with --force\033[0m\n'
    else
      printf '\033[33m    if it is the api container: docker compose stop api\033[0m\n'
    fi
    printf '\033[33m    or re-run with --port 7801\033[0m\n'
    exit 1
  fi
fi
echo "    free"

step 4 "Qdrant and $FRONTEND"
if [ "$SKIP_DOCKER" -eq 1 ]; then
  echo "    skipped"
else
  docker compose \
    -f docker/backend/compose.yml \
    -f docker/backend/compose.host-api.yml \
    up -d \
    || { echo "Backend containers could not be started." >&2; exit 1; }

  if [ "$FRONTEND" = frontend-admin ]; then
    docker compose \
      -f docker/frontend/compose.yml \
      -f docker/frontend/compose.host-api.yml \
      stop
    docker compose \
      -f docker/frontend/compose-admin.yml \
      -f docker/frontend/compose-admin.host-api.yml \
      up -d \
      || { echo "frontend-admin container could not be started." >&2; exit 1; }
  else
    docker compose \
      -f docker/frontend/compose-admin.yml \
      -f docker/frontend/compose-admin.host-api.yml \
      stop
    docker compose \
      -f docker/frontend/compose.yml \
      -f docker/frontend/compose.host-api.yml \
      up -d \
      || { echo "frontend container could not be started." >&2; exit 1; }
  fi

  printf '\033[32m    %s  http://localhost:7800\033[0m\n' "$FRONTEND"
  printf '\033[32m    qdrant   http://localhost:7833/dashboard\033[0m\n'
fi

step 5 "Corpus ingest"
.venv/bin/python scripts/ingest_corpus.py --direct \
  || { echo "Corpus ingestion failed." >&2; exit 1; }

step 6 "API on this machine"
printf '\033[32m    swagger  http://localhost:%s/docs\033[0m\n' "$PORT"
echo "    stop with Ctrl+C - the containers keep running"
echo

UVICORN_ARGS=(backend.main:app --port "$PORT")
[ "$NO_RELOAD" -eq 1 ] || UVICORN_ARGS+=(--reload)
[ "$BIND_ALL" -eq 1 ] && UVICORN_ARGS+=(--host 0.0.0.0)

if [ -x .venv/bin/uvicorn ]; then
  exec .venv/bin/uvicorn "${UVICORN_ARGS[@]}"
else
  exec .venv/bin/python -m uvicorn "${UVICORN_ARGS[@]}"
fi
