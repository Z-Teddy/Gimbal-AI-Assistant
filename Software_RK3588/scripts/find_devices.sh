#!/usr/bin/env bash
set -euo pipefail

print_section() {
  echo
  echo "== $1 =="
}

list_paths() {
  local pattern="$1"
  local show_target="$2"
  local found=0
  shopt -s nullglob
  local paths=(${pattern})
  shopt -u nullglob

  if [[ ${#paths[@]} -eq 0 ]]; then
    echo "  (none)"
    return
  fi

  local path
  for path in "${paths[@]}"; do
    found=1
    if [[ "${show_target}" == "target" && -L "${path}" ]]; then
      echo "  ${path} -> $(readlink -f "${path}")"
    else
      echo "  ${path}"
    fi
  done

  if [[ "${found}" -eq 0 ]]; then
    echo "  (none)"
  fi
}

first_match() {
  local pattern="$1"
  shopt -s nullglob
  local paths=(${pattern})
  shopt -u nullglob
  if [[ ${#paths[@]} -gt 0 ]]; then
    printf '%s\n' "${paths[0]}"
  fi
}

print_section "Video Devices"
list_paths "/dev/video*" "plain"

print_section "V4L By-ID"
list_paths "/dev/v4l/by-id/*" "target"

print_section "Serial Devices (/dev/ttyUSB*)"
list_paths "/dev/ttyUSB*" "plain"

print_section "Serial Devices (/dev/ttyACM*)"
list_paths "/dev/ttyACM*" "plain"

print_section "Serial By-ID"
list_paths "/dev/serial/by-id/*" "target"

recommended_camera_path="$(first_match "/dev/video*")"
recommended_camera_index=""
if [[ -n "${recommended_camera_path}" && "${recommended_camera_path}" =~ ^/dev/video([0-9]+)$ ]]; then
  recommended_camera_index="${BASH_REMATCH[1]}"
fi

recommended_serial_path="$(first_match "/dev/serial/by-id/*")"
if [[ -z "${recommended_serial_path}" ]]; then
  recommended_serial_path="$(first_match "/dev/ttyUSB*")"
fi
if [[ -z "${recommended_serial_path}" ]]; then
  recommended_serial_path="$(first_match "/dev/ttyACM*")"
fi

print_section "Suggested default.yaml Values"
if [[ -n "${recommended_camera_index}" ]]; then
  echo "camera:"
  echo "  index: ${recommended_camera_index}"
else
  echo "camera:"
  echo "  index: <请根据 /dev/videoN 手动填写>"
fi

if [[ -n "${recommended_serial_path}" ]]; then
  echo "serial:"
  echo "  port: \"${recommended_serial_path}\""
else
  echo "serial:"
  echo "  port: \"<请根据串口设备手动填写>\""
fi

echo
echo "提示:"
echo "  - camera.index 当前仍使用数值索引，建议结合 /dev/v4l/by-id 的指向关系确认对应摄像头。"
echo "  - serial.port 优先推荐使用 /dev/serial/by-id/*，这样比固定 /dev/ttyUSB0 更稳。"
echo "  - 本脚本只做设备发现与配置提示，不会修改 default.yaml。"
