#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
SECRET_FILE="$PROJECT_ROOT/.credentials"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: Python was not found. Install Python 3.11 or newer."
  exit 1
fi

python_version="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
  echo "Warning: Python $python_version detected; Python 3.11+ is recommended."
fi

if [[ -d "$VENV_DIR" && ! -x "$VENV_PYTHON" ]]; then
  echo "Error: .venv was created by another operating system."
  echo "Remove .venv and run this Linux setup script again."
  exit 1
elif [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating shared virtual environment..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "Using existing virtual environment: $VENV_DIR"
fi

echo "Installing project dependencies..."
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r "$PROJECT_ROOT/requirements.txt"

#####
# Only Azure values are secret
if [[ -f "$SECRET_FILE" ]]; then
  echo "Keeping existing Azure secrets: $SECRET_FILE"
else
  {
    echo "SECRET_AZURE_AI_ENDPOINT="
    echo "SECRET_AZURE_AI_AUTH=key"
    echo "SECRET_AZURE_AI_API_KEY="
    echo "SECRET_AZURE_AI_CHAT_DEPLOYMENT=gpt-5.1"
    echo "SECRET_AZURE_AI_EMBEDDING_DEPLOYMENT=text-embedding-3-small"
  } > "$SECRET_FILE"
  chmod 600 "$SECRET_FILE"
  echo "Created .credentials for Azure credentials."
fi

echo
echo "Setup complete."
echo "Next:"
echo "  1. Add your Azure credentials to .credentials."
echo "  2. Run ./scripts/linux/start-all.sh"
