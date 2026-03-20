#!/usr/bin/env bash
set -euo pipefail

RAW_WAV="/tmp/gimbal_voice_test/usb_asr.wav"
USB_CARD_LINE="$(arecord -l | grep -m1 'USB PnP Sound Device' || true)"

if [[ -z "${USB_CARD_LINE}" ]]; then
  echo "未检测到 USB 麦克风：USB PnP Sound Device"
  echo "请先插好 USB 麦克风，再执行 arecord -l 检查。"
  exit 1
fi

USB_CARD_NUM="$(echo "$USB_CARD_LINE" | sed -n 's/^card \([0-9]\+\):.*/\1/p')"

if [[ -z "${USB_CARD_NUM}" ]]; then
  echo "无法解析 USB 麦克风 card 编号"
  echo "$USB_CARD_LINE"
  exit 1
fi

DEVICE="plughw:${USB_CARD_NUM},0"

# 优先使用 gimbal 环境里的 python
if [[ -x "/home/orangepi/miniconda3/envs/gimbal/bin/python" ]]; then
  PYTHON_BIN="/home/orangepi/miniconda3/envs/gimbal/bin/python"
else
  PYTHON_BIN="python"
fi

mkdir -p /tmp/gimbal_voice_test

echo "== 使用设备: ${DEVICE} =="
echo "== 3秒录音开始，请现在说话 =="
arecord -D "${DEVICE}" -f S16_LE -r 16000 -c 1 -d 3 "${RAW_WAV}"

echo "== 文件信息 =="
file "${RAW_WAV}"

echo "== 识别结果 =="
"${PYTHON_BIN}" scripts/decode_wav.py "${RAW_WAV}"

echo
echo "wav: ${RAW_WAV}"
