#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : __init__.py
@Author  : Z-Teddy
@Brief   : 语音模块导出入口
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

from app.voice.command_parser import VoiceCommand, parse_command
from app.voice.config import (
    DEFAULT_CHANNELS,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_COOLDOWN_SEC,
    DEFAULT_MAX_SPEECH_SEC,
    DEFAULT_MIN_SPEECH_SEC,
    DEFAULT_RECORD_DEVICE_KEYWORD,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_SILENCE_SEC,
    MODEL_DIR,
    MODEL_PATH,
    TOKENS_PATH,
    VAD_MODEL_PATH,
    VoiceRuntimeConfig,
)
from app.voice.dispatcher import dispatch_command

__all__ = [
    "DEFAULT_CHANNELS",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_COOLDOWN_SEC",
    "DEFAULT_MAX_SPEECH_SEC",
    "DEFAULT_MIN_SPEECH_SEC",
    "DEFAULT_RECORD_DEVICE_KEYWORD",
    "DEFAULT_SAMPLE_RATE",
    "DEFAULT_SILENCE_SEC",
    "MODEL_DIR",
    "MODEL_PATH",
    "TOKENS_PATH",
    "VAD_MODEL_PATH",
    "VoiceCommand",
    "VoiceRuntimeConfig",
    "dispatch_command",
    "parse_command",
]

_LAZY_EXPORTS = {
    "decode_samples",
    "decode_wav",
    "AudioDeviceNotFoundError",
    "RuntimeBridgeResult",
    "apply_voice_command_to_runtime",
    "VoiceCommandBridge",
    "VoiceOverrideController",
    "VoiceOverrideSnapshot",
    "VoiceRecognitionResult",
    "VoiceRuntimeContext",
    "VoiceRuntimeEvent",
    "VoiceRealtimeListener",
    "VoiceRuntimeBridge",
}

__all__.extend(sorted(_LAZY_EXPORTS))


def __getattr__(name):
    if name in {"decode_samples", "decode_wav"}:
        from app.voice.asr_runner import decode_samples, decode_wav

        return {
            "decode_samples": decode_samples,
            "decode_wav": decode_wav,
        }[name]

    if name in {"AudioDeviceNotFoundError", "VoiceRecognitionResult", "VoiceRealtimeListener"}:
        from app.voice.realtime_listener import (
            AudioDeviceNotFoundError,
            VoiceRecognitionResult,
            VoiceRealtimeListener,
        )

        return {
            "AudioDeviceNotFoundError": AudioDeviceNotFoundError,
            "VoiceRecognitionResult": VoiceRecognitionResult,
            "VoiceRealtimeListener": VoiceRealtimeListener,
        }[name]

    if name in {"VoiceOverrideController", "VoiceOverrideSnapshot"}:
        from app.voice.override_state import VoiceOverrideController, VoiceOverrideSnapshot

        return {
            "VoiceOverrideController": VoiceOverrideController,
            "VoiceOverrideSnapshot": VoiceOverrideSnapshot,
        }[name]

    if name in {
        "RuntimeBridgeResult",
        "VoiceCommandBridge",
        "VoiceRuntimeBridge",
        "VoiceRuntimeContext",
        "VoiceRuntimeEvent",
        "apply_voice_command_to_runtime",
    }:
        from app.voice.runtime_bridge import (
            RuntimeBridgeResult,
            VoiceCommandBridge,
            VoiceRuntimeBridge,
            VoiceRuntimeContext,
            VoiceRuntimeEvent,
            apply_voice_command_to_runtime,
        )

        return {
            "RuntimeBridgeResult": RuntimeBridgeResult,
            "VoiceCommandBridge": VoiceCommandBridge,
            "VoiceRuntimeContext": VoiceRuntimeContext,
            "VoiceRuntimeEvent": VoiceRuntimeEvent,
            "VoiceRuntimeBridge": VoiceRuntimeBridge,
            "apply_voice_command_to_runtime": apply_voice_command_to_runtime,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
