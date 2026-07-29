#!/usr/bin/env bash
# Runs the backend with the server-rendered administration frontend.
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "$SCRIPT_DIR/dev.sh" "$@" --frontend frontend-admin
