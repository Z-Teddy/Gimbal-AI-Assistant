#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : dispatcher.py
@Author  : Z-Teddy
@Brief   : 语音命令派发层
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

from app.voice.command_parser import VoiceCommand


_ACTION_MAP = {
    VoiceCommand.TRACK: "set_mode:TRACK",
    VoiceCommand.HOLD: "set_mode:HOLD",
    VoiceCommand.SCAN: "set_mode:SCAN",
    VoiceCommand.HOME: "set_mode:HOME",
    VoiceCommand.OPEN_CAMERA: "camera:open",
    VoiceCommand.CLOSE_CAMERA: "camera:close",
    VoiceCommand.UNKNOWN: "noop",
}


def dispatch_command(cmd: VoiceCommand) -> str:
    """
    返回当前命令对应的标准动作字符串。

    当前版本先保持为本地动作描述，不直接改动 v3.0 主程序。
    后续可在这里接入主线程消息队列，或桥接到 SerialController.send_mode()
    / CameraManager 的控制入口，避免深改 main.py 主循环。
    """
    return _ACTION_MAP.get(cmd, "noop")
