#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : command_parser.py
@Author  : Z-Teddy
@Brief   : 语音命令词解析
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import re
from enum import Enum


class VoiceCommand(str, Enum):
    TRACK = "TRACK"
    HOLD = "HOLD"
    SCAN = "SCAN"
    HOME = "HOME"
    OPEN_CAMERA = "OPEN_CAMERA"
    CLOSE_CAMERA = "CLOSE_CAMERA"
    UNKNOWN = "UNKNOWN"


_PUNCTUATION_RE = re.compile(r"<\|.*?\|>|[\s,，。！？!?.、；;:：\"'“”‘’（）()【】\[\]/\\-]+")

_EXACT_RULES = (
    (VoiceCommand.CLOSE_CAMERA, ("关闭摄像头", "关掉摄像头")),
    (VoiceCommand.OPEN_CAMERA, ("打开摄像头", "开启摄像头")),
    (VoiceCommand.HOLD, ("停止跟踪", "停止追踪", "停止", "保持", "待机")),
    (VoiceCommand.SCAN, ("开始扫描", "扫描", "搜索目标", "搜索")),
    (VoiceCommand.HOME, ("回到中位", "回中", "归位", "回家")),
    (VoiceCommand.TRACK, ("开始跟踪", "开始追踪", "跟踪目标", "跟踪", "追踪")),
)


def _normalize_text(text: str) -> str:
    return _PUNCTUATION_RE.sub("", text.strip().lower())


def parse_command(text: str) -> VoiceCommand:
    """
    将识别文本映射为固定命令词。

    Args:
        text (str): ASR 识别文本

    Returns:
        VoiceCommand: 解析后的命令
    """
    if not isinstance(text, str):
        return VoiceCommand.UNKNOWN

    normalized = _normalize_text(text)
    if len(normalized) < 2:
        return VoiceCommand.UNKNOWN

    for command, variants in _EXACT_RULES:
        if any(variant in normalized for variant in variants):
            return command

    if "摄像头" in normalized:
        if "关闭" in normalized or "关掉" in normalized:
            return VoiceCommand.CLOSE_CAMERA
        if "打开" in normalized or "开启" in normalized:
            return VoiceCommand.OPEN_CAMERA

    if "停止" in normalized or "保持" in normalized or "待机" in normalized:
        return VoiceCommand.HOLD

    if "扫描" in normalized or "搜索" in normalized:
        return VoiceCommand.SCAN

    if "回中" in normalized or "中位" in normalized or "归位" in normalized or "回家" in normalized:
        return VoiceCommand.HOME

    if "跟踪" in normalized or "追踪" in normalized:
        return VoiceCommand.TRACK

    return VoiceCommand.UNKNOWN
