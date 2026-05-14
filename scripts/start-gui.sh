#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'EOF'
Usage: scripts/start-gui.sh [--setup [bootstrap options]]

Starts the MOMO GUI. If .venv does not exist yet, it runs scripts/bootstrap.sh
first. Bootstrap auto-installs common system packages when possible. Use
--setup to force a bootstrap refresh before launching.

Examples:
  scripts/start-gui.sh
  scripts/start-gui.sh --setup --model qwen3.5:9b
  MOMO_GUI_PORT=8502 scripts/start-gui.sh
  SKIP_MODEL=1 scripts/start-gui.sh
EOF
}

FORCE_SETUP=0
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

if [ "${1:-}" = "--setup" ]; then
  FORCE_SETUP=1
  shift
fi

venv_is_supported() {
  [ -x ".venv/bin/python" ] || return 1
  .venv/bin/python - <<'PY' >/dev/null 2>&1
import sys

raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}

if [ "$FORCE_SETUP" = "1" ] || ! venv_is_supported; then
  scripts/bootstrap.sh "$@"
elif [ "$#" -gt 0 ]; then
  echo "Unknown option for an existing setup: $1" >&2
  echo "Use --setup to pass bootstrap options." >&2
  usage >&2
  exit 2
fi

exec scripts/run-gui.sh
