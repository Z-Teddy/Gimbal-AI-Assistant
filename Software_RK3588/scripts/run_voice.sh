#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if [[ -n "${PYTHON_BIN:-}" && -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON_BIN}"
elif [[ -x "${PROJECT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"
elif [[ -x "${PROJECT_DIR}/venv/bin/python" ]]; then
  PYTHON_BIN="${PROJECT_DIR}/venv/bin/python"
elif [[ -n "${CONDA_PREFIX:-}" && -x "${CONDA_PREFIX}/bin/python" ]]; then
  PYTHON_BIN="${CONDA_PREFIX}/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  echo "[run_voice] No suitable Python interpreter found." >&2
  echo "[run_voice] You can export PYTHON_BIN=/path/to/python before running." >&2
  exit 1
fi

has_arg() {
  local expected="$1"
  shift
  local arg
  for arg in "$@"; do
    if [[ "${arg}" == "${expected}" ]]; then
      return 0
    fi
  done
  return 1
}

CONFIG_PATH="${RUN_CONFIG:-configs/runtime_voice.yaml}"
CMD=(main.py)

if ! has_arg "--gui" "$@" && ! has_arg "--headless" "$@"; then
  CMD+=("--gui")
fi

if ! has_arg "--config" "$@"; then
  CMD+=("--config" "${CONFIG_PATH}")
fi

CMD+=("$@")

cd "${PROJECT_DIR}"
exec "${PYTHON_BIN}" "${CMD[@]}"
