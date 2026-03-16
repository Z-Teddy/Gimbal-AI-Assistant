#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="gimbal-ai.service"
INSTALL_PATH="/etc/systemd/system/${SERVICE_NAME}"

if [[ "${EUID}" -eq 0 ]]; then
  SYSTEMCTL_PREFIX=()
else
  if ! command -v sudo >/dev/null 2>&1; then
    echo "[uninstall_service] 需要 root 权限卸载 systemd 系统服务，且当前未找到 sudo。" >&2
    exit 1
  fi
  SYSTEMCTL_PREFIX=(sudo)
fi

"${SYSTEMCTL_PREFIX[@]}" systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
"${SYSTEMCTL_PREFIX[@]}" systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
"${SYSTEMCTL_PREFIX[@]}" rm -f "${INSTALL_PATH}"
"${SYSTEMCTL_PREFIX[@]}" systemctl daemon-reload
"${SYSTEMCTL_PREFIX[@]}" systemctl reset-failed "${SERVICE_NAME}" 2>/dev/null || true

echo "[uninstall_service] 已停止并卸载 ${SERVICE_NAME}"
echo "[uninstall_service] 未删除日志目录、配置文件或仓库内容。"
