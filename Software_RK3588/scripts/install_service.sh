#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOFTWARE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd -- "${SOFTWARE_DIR}/.." && pwd)"
TEMPLATE_PATH="${SOFTWARE_DIR}/services/gimbal-ai.service"
SERVICE_NAME="gimbal-ai.service"
INSTALL_PATH="/etc/systemd/system/${SERVICE_NAME}"
RUN_USER="${RUN_USER:-${SUDO_USER:-$(id -un)}}"

if [[ ! -f "${TEMPLATE_PATH}" ]]; then
  echo "[install_service] service 模板不存在: ${TEMPLATE_PATH}" >&2
  exit 1
fi

if [[ "${EUID}" -eq 0 ]]; then
  SYSTEMCTL_PREFIX=()
else
  if ! command -v sudo >/dev/null 2>&1; then
    echo "[install_service] 需要 root 权限安装 systemd 系统服务，且当前未找到 sudo。" >&2
    exit 1
  fi
  SYSTEMCTL_PREFIX=(sudo)
fi

if [[ -x "${SOFTWARE_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${SOFTWARE_DIR}/.venv/bin/python"
elif [[ -x "${SOFTWARE_DIR}/venv/bin/python" ]]; then
  PYTHON_BIN="${SOFTWARE_DIR}/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  echo "[install_service] 未找到可用的 Python 解释器（优先 .venv/venv，其次系统 python3）。" >&2
  exit 1
fi

escape_sed_replacement() {
  printf '%s' "$1" | sed -e 's/[\/&]/\\&/g'
}

rendered_service="$(mktemp)"
trap 'rm -f "${rendered_service}"' EXIT

sed \
  -e "s|{{RUN_USER}}|$(escape_sed_replacement "${RUN_USER}")|g" \
  -e "s|{{PROJECT_ROOT}}|$(escape_sed_replacement "${PROJECT_ROOT}")|g" \
  -e "s|{{SOFTWARE_DIR}}|$(escape_sed_replacement "${SOFTWARE_DIR}")|g" \
  -e "s|{{PYTHON_BIN}}|$(escape_sed_replacement "${PYTHON_BIN}")|g" \
  "${TEMPLATE_PATH}" > "${rendered_service}"

"${SYSTEMCTL_PREFIX[@]}" install -m 0644 "${rendered_service}" "${INSTALL_PATH}"
"${SYSTEMCTL_PREFIX[@]}" systemctl daemon-reload
"${SYSTEMCTL_PREFIX[@]}" systemctl enable "${SERVICE_NAME}"
"${SYSTEMCTL_PREFIX[@]}" systemctl restart "${SERVICE_NAME}"

echo "[install_service] 已安装 systemd 系统服务: ${INSTALL_PATH}"
echo "[install_service] 运行用户: ${RUN_USER}"
echo "[install_service] 工作目录: ${SOFTWARE_DIR}"
echo "[install_service] Python: ${PYTHON_BIN}"
echo
echo "建议检查命令:"
echo "  sudo systemctl status ${SERVICE_NAME} --no-pager"
echo "  sudo journalctl -u ${SERVICE_NAME} -n 100 --no-pager"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"
