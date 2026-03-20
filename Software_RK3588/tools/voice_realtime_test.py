#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : voice_realtime_test.py
@Author  : Z-Teddy
@Brief   : 实时语音监听独立测试工具
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import argparse
import logging
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.voice.config import DEFAULT_COOLDOWN_SEC, DEFAULT_RECORD_DEVICE_KEYWORD, VoiceRuntimeConfig
from app.voice.realtime_listener import VoiceRecognitionResult, VoiceRealtimeListener
from app.voice.runtime_bridge import VoiceRuntimeBridge


def parse_args():
    parser = argparse.ArgumentParser(description="实时长驻语音监听测试工具")
    parser.add_argument(
        "--device-keyword",
        default=DEFAULT_RECORD_DEVICE_KEYWORD,
        help="用于从 arecord -l 中匹配 USB 麦克风的关键字",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=DEFAULT_COOLDOWN_SEC,
        help="同一动作的冷却时间，单位秒",
    )
    parser.add_argument(
        "--gain",
        type=float,
        default=1.0,
        help="软件输入增益，默认 1.0",
    )
    parser.add_argument(
        "--max-speech-sec",
        type=float,
        default=8.0,
        help="单段语音最长时长，默认 8.0 秒",
    )
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=0.35,
        help="Silero VAD 阈值，默认 0.35",
    )
    parser.add_argument(
        "--min-speech-sec",
        type=float,
        default=0.3,
        help="最短语音段时长，默认 0.3 秒",
    )
    parser.add_argument(
        "--silence-sec",
        type=float,
        default=0.6,
        help="结束判定静音时长，默认 0.6 秒",
    )
    parser.add_argument(
        "--execute-actions",
        action="store_true",
        help="识别成功后，真正桥接到当前仓库的 serial/camera 控制",
    )
    parser.add_argument("--debug", action="store_true", help="输出更详细的调试日志")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    runtime_config = VoiceRuntimeConfig(
        record_device_keyword=args.device_keyword,
        cooldown_sec=args.cooldown,
        max_speech_sec=args.max_speech_sec,
        input_gain=args.gain,
        vad_threshold=args.vad_threshold,
        min_speech_sec=args.min_speech_sec,
        silence_sec=args.silence_sec,
    )
    listener = VoiceRealtimeListener(runtime_config=runtime_config, debug=args.debug)
    runtime_bridge = VoiceRuntimeBridge() if args.execute_actions else None

    print(
        f"开始实时语音监听，device_keyword={runtime_config.record_device_keyword!r}，按 Ctrl+C 退出。",
        flush=True,
    )
    print(
        f"语音调优: gain={runtime_config.input_gain:.1f}x max_speech={runtime_config.max_speech_sec:.2f}s vad_threshold={runtime_config.vad_threshold:.2f} min_speech={runtime_config.min_speech_sec:.2f}s silence={runtime_config.silence_sec:.2f}s",
        flush=True,
    )
    if args.execute_actions:
        print("已开启真实动作执行：mode 命令将走 SerialController，camera 命令将走 CameraManager。", flush=True)

    def handle_result(result: VoiceRecognitionResult) -> None:
        print(f"ASR: {result.text}", flush=True)
        print(f"CMD: {result.command.value}", flush=True)
        print(f"ACTION: {result.action}", flush=True)
        if args.debug and result.segment_path:
            print(f"SEGMENT: {result.segment_path}", flush=True)

        if runtime_bridge is not None and not result.suppressed and result.raw_action != "noop":
            bridge_result = runtime_bridge.execute(result.command)
            logging.getLogger(__name__).info(
                "动作执行: success=%s detail=%s action=%s",
                bridge_result.success,
                bridge_result.detail,
                bridge_result.action,
            )

        print("", flush=True)

    try:
        listener.run_forever(on_result=handle_result)
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，语音监听已退出。", flush=True)
    finally:
        listener.stop()
        if runtime_bridge is not None:
            runtime_bridge.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
