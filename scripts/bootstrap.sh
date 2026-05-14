#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODEL="${MOMO_LLM_MODEL:-qwen3.5:9b}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu124}"
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"
PYTHON_BIN="${PYTHON_BIN:-}"
SKIP_OLLAMA="${SKIP_OLLAMA:-0}"
SKIP_MODEL="${SKIP_MODEL:-0}"
SKIP_SYSTEM_DEPS="${SKIP_SYSTEM_DEPS:-0}"
UV_BIN="${UV_BIN:-}"

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap.sh [options]

Options:
  --model NAME       Ollama model to pull (default: qwen3.5:9b)
  --python PATH      Python interpreter to use (default: Python 3.10+ auto-detect)
  --skip-ollama      Do not install/start Ollama
  --skip-model       Do not pull the Ollama model
  --skip-system-deps Do not auto-install curl/ffmpeg/python system packages
  -h, --help         Show this help

Environment variables:
  MOMO_LLM_MODEL     Default model name
  TORCH_INDEX_URL    PyTorch wheel index (default: CUDA 12.4 wheels)
  PYTHON_BIN         Python interpreter override
  PYTHON_VERSION     uv-managed Python version if system Python is too old (default: 3.10)
  SKIP_OLLAMA=1      Same as --skip-ollama
  SKIP_MODEL=1       Same as --skip-model
  SKIP_SYSTEM_DEPS=1 Same as --skip-system-deps
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --model)
      MODEL="${2:?missing model name}"
      shift 2
      ;;
    --python)
      PYTHON_BIN="${2:?missing python path}"
      shift 2
      ;;
    --skip-ollama)
      SKIP_OLLAMA=1
      shift
      ;;
    --skip-model)
      SKIP_MODEL=1
      shift
      ;;
    --skip-system-deps)
      SKIP_SYSTEM_DEPS=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

say() {
  printf '\n==> %s\n' "$*"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

python_is_supported() {
  "$1" - <<'PY' >/dev/null 2>&1
import sys

raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
}

find_supported_python() {
  if [ -n "$PYTHON_BIN" ]; then
    if python_is_supported "$PYTHON_BIN"; then
      return 0
    fi
    echo "Python override is too old: $("$PYTHON_BIN" --version 2>&1)" >&2
    echo "MOMO requires Python 3.10 or newer." >&2
    exit 1
  fi

  local candidate
  for candidate in python3.10 python3.11 python3.12 python3.13 python3; do
    if need_cmd "$candidate" && python_is_supported "$candidate"; then
      PYTHON_BIN="$candidate"
      return 0
    fi
  done
  return 1
}

sudo_prefix() {
  if [ "$(id -u)" -eq 0 ]; then
    return 0
  fi
  if need_cmd sudo; then
    printf 'sudo'
    return 0
  fi
  return 1
}

run_privileged() {
  local sudo_bin
  sudo_bin="$(sudo_prefix || true)"
  if [ -n "$sudo_bin" ]; then
    "$sudo_bin" "$@"
  elif [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    echo "Need sudo/root to install missing system packages: $*" >&2
    exit 1
  fi
}

install_system_deps() {
  if [ "$SKIP_SYSTEM_DEPS" = "1" ]; then
    return 0
  fi

  local needs_install=0
  if ! need_cmd curl; then
    needs_install=1
  fi
  if ! need_cmd ffmpeg; then
    needs_install=1
  fi
  if [ "$needs_install" = "0" ]; then
    return 0
  fi

  say "Installing missing system packages"
  if need_cmd apt-get; then
    run_privileged apt-get update
    run_privileged apt-get install -y curl ffmpeg python3 python3-venv python3-pip
    return 0
  fi
  if need_cmd dnf; then
    run_privileged dnf install -y curl ffmpeg python3 python3-pip
    return 0
  fi
  if need_cmd yum; then
    run_privileged yum install -y curl ffmpeg python3 python3-pip
    return 0
  fi
  if need_cmd pacman; then
    run_privileged pacman -Sy --noconfirm --needed curl ffmpeg python python-pip
    return 0
  fi
  if need_cmd zypper; then
    run_privileged zypper --non-interactive install curl ffmpeg python3 python3-pip
    return 0
  fi
  if need_cmd apk; then
    run_privileged apk add curl ffmpeg python3 py3-pip
    return 0
  fi

  cat >&2 <<'EOF'
Could not find a supported package manager to auto-install system packages.
Install curl, ffmpeg, Python 3.10+, and Python venv support, then rerun.
EOF
  exit 1
}

install_uv_user_local() {
  if [ -n "$UV_BIN" ] && [ -x "$UV_BIN" ]; then
    return 0
  fi
  if need_cmd uv; then
    UV_BIN="$(command -v uv)"
    return 0
  fi
  if [ -x "$HOME/.local/bin/uv" ]; then
    UV_BIN="$HOME/.local/bin/uv"
    return 0
  fi

  say "Installing uv for user-local Python management"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  UV_BIN="$HOME/.local/bin/uv"
  if [ ! -x "$UV_BIN" ]; then
    echo "uv installation finished, but $UV_BIN was not found." >&2
    exit 1
  fi
}

ensure_supported_python() {
  if find_supported_python; then
    return 0
  fi
  if [ "$SKIP_SYSTEM_DEPS" = "1" ]; then
    cat >&2 <<'EOF'
Python 3.10 or newer is required, and no supported interpreter was found.
Rerun without SKIP_SYSTEM_DEPS=1 so MOMO can install user-local Python via uv,
or pass --python /path/to/python3.10.
EOF
    exit 1
  fi

  install_uv_user_local
  say "Installing Python ${PYTHON_VERSION} with uv"
  "$UV_BIN" python install "$PYTHON_VERSION"
  PYTHON_BIN="$("$UV_BIN" python find "$PYTHON_VERSION")"
  if ! python_is_supported "$PYTHON_BIN"; then
    echo "uv installed Python, but it is not usable: $("$PYTHON_BIN" --version 2>&1)" >&2
    exit 1
  fi
}

ensure_venv_support() {
  local tmp_dir
  tmp_dir="$(mktemp -d)"
  if "$PYTHON_BIN" -m venv "$tmp_dir" >/dev/null 2>&1; then
    rm -rf "$tmp_dir"
    return 0
  fi
  rm -rf "$tmp_dir"

  if [ "$SKIP_SYSTEM_DEPS" != "1" ]; then
    say "Installing Python venv support"
    if need_cmd apt-get; then
      run_privileged apt-get update
      local python_cmd
      python_cmd="$(basename "$PYTHON_BIN")"
      run_privileged apt-get install -y "${python_cmd}-venv" python3-pip \
        || run_privileged apt-get install -y python3-venv python3-pip
    elif need_cmd dnf; then
      run_privileged dnf install -y python3 python3-pip
    elif need_cmd yum; then
      run_privileged yum install -y python3 python3-pip
    elif need_cmd pacman; then
      run_privileged pacman -Sy --noconfirm --needed python python-pip
    elif need_cmd zypper; then
      run_privileged zypper --non-interactive install python3 python3-pip
    elif need_cmd apk; then
      run_privileged apk add python3 py3-pip
    fi
  fi

  tmp_dir="$(mktemp -d)"
  if "$PYTHON_BIN" -m venv "$tmp_dir" >/dev/null 2>&1; then
    rm -rf "$tmp_dir"
    return 0
  fi
  rm -rf "$tmp_dir"

  cat >&2 <<'EOF'
Python venv support is still unavailable.
On Ubuntu/Debian this usually means `python3-venv` could not be installed.
EOF
  exit 1
}

refresh_existing_venv_if_needed() {
  if [ ! -x ".venv/bin/python" ]; then
    return 0
  fi
  if python_is_supported ".venv/bin/python"; then
    return 0
  fi
  say "Replacing unsupported .venv Python: $(.venv/bin/python --version 2>&1)"
  rm -rf .venv
}

install_system_deps
ensure_supported_python

if ! need_cmd curl; then
  echo "curl is required but could not be installed automatically." >&2
  exit 1
fi

if ! need_cmd nvidia-smi; then
  echo "nvidia-smi is required. Install a working NVIDIA driver before MOMO." >&2
  exit 1
fi

say "Using Python: $("$PYTHON_BIN" --version)"
"$PYTHON_BIN" - <<'PY'
import sys

if sys.version_info < (3, 10):
    sys.stderr.write(
        "Python 3.10 or newer is required for the supported GPU install path.\n"
    )
    raise SystemExit(1)
PY

if ! need_cmd ffmpeg; then
  echo "ffmpeg is required but could not be installed automatically." >&2
  exit 1
fi

ensure_venv_support
refresh_existing_venv_if_needed

say "Creating/updating .venv"
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel

say "Installing PyTorch"
.venv/bin/python -m pip install torch torchaudio --index-url "$TORCH_INDEX_URL"

say "Checking CUDA GPU visibility"
.venv/bin/python - <<'PY'
import sys

import torch

if not torch.cuda.is_available():
    sys.stderr.write(
        "CUDA GPU is required, but PyTorch cannot see one. "
        "Check the NVIDIA driver/CUDA runtime before running MOMO.\n"
    )
    raise SystemExit(1)

print("CUDA available: {0}".format(torch.cuda.get_device_name(0)))
PY

say "Installing MOMO"
.venv/bin/python -m pip install -e '.[gui,asr]'

OLLAMA_BIN="${OLLAMA_BIN:-}"
if [ -z "$OLLAMA_BIN" ]; then
  if need_cmd ollama; then
    OLLAMA_BIN="$(command -v ollama)"
  else
    OLLAMA_BIN="$HOME/.local/bin/ollama"
  fi
fi

install_ollama_user_local() {
  local machine
  machine="$(uname -m)"
  if [ "$machine" != "x86_64" ]; then
    echo "User-local Ollama bootstrap currently supports x86_64 Linux only, got: $machine" >&2
    echo "Install Ollama manually, then rerun with --skip-ollama." >&2
    exit 1
  fi
  local archive
  archive="$(mktemp /tmp/ollama-linux-amd64.XXXXXX.tar.zst)"
  trap 'rm -f "$archive"' EXIT
  say "Installing Ollama into ~/.local"
  mkdir -p "$HOME/.local"
  .venv/bin/python -m pip install zstandard
  curl -L --fail --show-error --progress-bar \
    -o "$archive" \
    https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.zst
  .venv/bin/python - "$archive" "$HOME/.local" <<'PY'
from pathlib import Path
import sys
import tarfile
import zstandard as zstd

archive = Path(sys.argv[1])
dest = Path(sys.argv[2])
dest.mkdir(parents=True, exist_ok=True)
root = dest.resolve()
with archive.open("rb") as fh:
    reader = zstd.ZstdDecompressor().stream_reader(fh)
    with tarfile.open(fileobj=reader, mode="r|") as tf:
        for member in tf:
            target = (dest / member.name).resolve()
            if not str(target).startswith(str(root)):
                raise RuntimeError(f"unsafe archive path: {member.name}")
            tf.extract(member, path=dest)
PY
}

wait_for_ollama() {
  local deadline=$((SECONDS + 30))
  until curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; do
    if [ "$SECONDS" -gt "$deadline" ]; then
      echo "Ollama did not become ready. See .momo/ollama.log" >&2
      exit 1
    fi
    sleep 1
  done
}

if [ "$SKIP_OLLAMA" != "1" ]; then
  if [ ! -x "$OLLAMA_BIN" ]; then
    install_ollama_user_local
  fi
  say "Starting Ollama"
  mkdir -p .momo
  if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-1m}" \
      nohup "$OLLAMA_BIN" serve > .momo/ollama.log 2>&1 &
  fi
  wait_for_ollama

  if [ "$SKIP_MODEL" != "1" ]; then
    say "Pulling Ollama model: $MODEL"
    "$OLLAMA_BIN" pull "$MODEL"
  fi
fi

cat <<EOF

MOMO is ready.

Start the GUI:
  scripts/start-gui.sh

Then open:
  the URL printed by scripts/start-gui.sh (usually http://localhost:8501)

If ~/.local/bin is not on PATH, this repo still uses:
  $OLLAMA_BIN
EOF
