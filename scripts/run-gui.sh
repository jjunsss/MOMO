#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODEL="${MOMO_LLM_MODEL:-qwen3.5:9b}"
REQUESTED_PORT="${MOMO_GUI_PORT:-}"
PORT="${REQUESTED_PORT:-8501}"
PROVIDER="${MOMO_LLM_PROVIDER:-ollama}"
BASE_URL="${MOMO_LLM_BASE_URL:-http://localhost:11434}"
MANAGE_OLLAMA="${MOMO_MANAGE_OLLAMA:-auto}"
SKIP_MODEL="${SKIP_MODEL:-0}"
OLLAMA_BIN="${OLLAMA_BIN:-}"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is missing; running bootstrap to install system dependencies..."
  scripts/bootstrap.sh --skip-ollama --skip-model
fi

if [ ! -x ".venv/bin/python" ]; then
  echo ".venv not found. Run scripts/bootstrap.sh first." >&2
  exit 1
fi

.venv/bin/python - <<'PY'
import sys

if sys.version_info < (3, 10):
    sys.stderr.write(
        ".venv uses Python {0}.{1}, but MOMO requires Python 3.10+.\n"
        "Run scripts/start-gui.sh --setup to rebuild the environment.\n".format(
            sys.version_info.major,
            sys.version_info.minor,
        )
    )
    raise SystemExit(1)
PY

.venv/bin/python - <<'PY'
import sys

import torch

if not torch.cuda.is_available():
    sys.stderr.write(
        "CUDA GPU is required, but PyTorch cannot see one. "
        "MOMO will not fall back to CPU ASR.\n"
    )
    raise SystemExit(1)

print("CUDA available: {0}".format(torch.cuda.get_device_name(0)))
PY

port_is_free() {
  .venv/bin/python - "$1" <<'PY' >/dev/null 2>&1
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", port))
    except OSError:
        raise SystemExit(1)
PY
}

select_gui_port() {
  if [ -n "$REQUESTED_PORT" ]; then
    if port_is_free "$PORT"; then
      return 0
    fi
    echo "Port ${PORT} is already in use. Set MOMO_GUI_PORT to another port." >&2
    exit 1
  fi

  local candidate
  for candidate in 8501 8502 8503 8504 8505 8506 8507 8508 8509 8510; do
    if port_is_free "$candidate"; then
      PORT="$candidate"
      return 0
    fi
  done

  echo "No free GUI port found in 8501-8510. Set MOMO_GUI_PORT manually." >&2
  exit 1
}

is_local_ollama_url() {
  case "$BASE_URL" in
    http://localhost:*|http://127.0.0.1:*|http://0.0.0.0:*) return 0 ;;
    http://localhost|http://127.0.0.1|http://0.0.0.0) return 0 ;;
    *) return 1 ;;
  esac
}

should_manage_ollama() {
  if [ "$MANAGE_OLLAMA" = "1" ]; then
    return 0
  fi
  if [ "$MANAGE_OLLAMA" = "0" ]; then
    return 1
  fi
  is_local_ollama_url
}

ollama_host_value() {
  printf '%s\n' "$BASE_URL" | sed -E 's#^https?://##'
}

wait_for_ollama_url() {
  local deadline=$((SECONDS + 30))
  until curl -fsS "${BASE_URL%/}/api/tags" >/dev/null 2>&1; do
    if [ "$SECONDS" -gt "$deadline" ]; then
      echo "Ollama did not become ready at ${BASE_URL}." >&2
      if should_manage_ollama; then
        echo "See .momo/ollama.log for the local Ollama server log." >&2
      fi
      exit 1
    fi
    sleep 1
  done
}

check_ollama_model() {
  .venv/bin/python - "$BASE_URL" "$MODEL" <<'PY'
import json
import sys
import urllib.request

base_url = sys.argv[1].rstrip("/")
model = sys.argv[2]
with urllib.request.urlopen(f"{base_url}/api/tags", timeout=10) as response:
    payload = json.loads(response.read().decode("utf-8"))
available = {
    str(item.get("name") or item.get("model") or "").strip()
    for item in payload.get("models", [])
    if isinstance(item, dict)
}
if model and model not in available:
    sample = ", ".join(sorted(available)[:5]) or "none"
    sys.stderr.write(
        f"Ollama model '{model}' is not available at {base_url}. "
        f"Visible models: {sample}\n"
    )
    raise SystemExit(1)
PY
}

if [ "$PROVIDER" = "ollama" ]; then
  if should_manage_ollama; then
    if [ -z "$OLLAMA_BIN" ]; then
      if command -v ollama >/dev/null 2>&1; then
        OLLAMA_BIN="$(command -v ollama)"
      else
        OLLAMA_BIN="$HOME/.local/bin/ollama"
      fi
    fi
    if [ ! -x "$OLLAMA_BIN" ]; then
      echo "Ollama not found. Run scripts/bootstrap.sh first." >&2
      exit 1
    fi

    mkdir -p .momo
    if ! curl -fsS "${BASE_URL%/}/api/tags" >/dev/null 2>&1; then
      echo "Starting Ollama..."
      OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-1m}" \
        OLLAMA_HOST="$(ollama_host_value)" \
        nohup "$OLLAMA_BIN" serve > .momo/ollama.log 2>&1 &
    fi
    wait_for_ollama_url

    if ! OLLAMA_HOST="$BASE_URL" "$OLLAMA_BIN" list | awk '{print $1}' | grep -Fx "$MODEL" >/dev/null 2>&1; then
      if [ "$SKIP_MODEL" = "1" ]; then
        echo "Model $MODEL is missing, and SKIP_MODEL=1 disables automatic pull." >&2
        exit 1
      fi
      echo "Pulling missing model: $MODEL"
      OLLAMA_HOST="$BASE_URL" "$OLLAMA_BIN" pull "$MODEL"
    fi
  else
    wait_for_ollama_url
    check_ollama_model
  fi
fi

select_gui_port

export MOMO_LLM_PROVIDER="$PROVIDER"
export MOMO_LLM_MODEL="$MODEL"
export MOMO_LLM_BASE_URL="$BASE_URL"
export MOMO_ASR_DEVICE="${MOMO_ASR_DEVICE:-cuda}"

echo "Starting MOMO GUI at http://localhost:${PORT}"
exec .venv/bin/streamlit run src/meeting_ai/app/streamlit_app.py \
  --server.address=0.0.0.0 \
  --server.port="$PORT" \
  --server.headless=true \
  --server.runOnSave=false \
  --browser.gatherUsageStats=false
