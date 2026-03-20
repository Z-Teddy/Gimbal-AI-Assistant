#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : config.py
@Author  : Z-Teddy
@Brief   : 语音模块默认配置
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_DIR = (
    BASE_DIR
    / "models"
    / "asr"
    / "sherpa"
    / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
)
MODEL_PATH = MODEL_DIR / "model.int8.onnx"
TOKENS_PATH = MODEL_DIR / "tokens.txt"
VAD_MODEL_PATH = BASE_DIR / "models" / "asr" / "sherpa" / "silero_vad.onnx"

DEFAULT_RECORD_DEVICE_KEYWORD = "USB PnP Sound Device"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_CHUNK_SIZE = 1024
DEFAULT_COOLDOWN_SEC = 1.5
DEFAULT_MAX_SPEECH_SEC = 8.0
DEFAULT_MIN_SPEECH_SEC = 0.3
DEFAULT_SILENCE_SEC = 0.6
DEFAULT_VAD_THRESHOLD = 0.35
DEFAULT_INPUT_GAIN = 1.0
DEFAULT_DEBUG_LOG_INTERVAL_SEC = 1.0
DEFAULT_DEBUG_DUMP_DIR = Path("/tmp/gimbal_voice_debug")

DEFAULT_ASR_NUM_THREADS = 2
DEFAULT_VAD_BUFFER_SEC = 30.0
DEFAULT_RETRY_INTERVAL_SEC = 2.0


@dataclass(frozen=True)
class VoiceRuntimeConfig:
    """语音线程运行时配置。"""

    model_dir: Path = MODEL_DIR
    model_path: Path = MODEL_PATH
    tokens_path: Path = TOKENS_PATH
    vad_model_path: Path = VAD_MODEL_PATH
    record_device_keyword: str = DEFAULT_RECORD_DEVICE_KEYWORD
    sample_rate: int = DEFAULT_SAMPLE_RATE
    channels: int = DEFAULT_CHANNELS
    chunk_size: int = DEFAULT_CHUNK_SIZE
    cooldown_sec: float = DEFAULT_COOLDOWN_SEC
    max_speech_sec: float = DEFAULT_MAX_SPEECH_SEC
    min_speech_sec: float = DEFAULT_MIN_SPEECH_SEC
    silence_sec: float = DEFAULT_SILENCE_SEC
    vad_threshold: float = DEFAULT_VAD_THRESHOLD
    input_gain: float = DEFAULT_INPUT_GAIN
    asr_num_threads: int = DEFAULT_ASR_NUM_THREADS
    vad_buffer_sec: float = DEFAULT_VAD_BUFFER_SEC
    retry_interval_sec: float = DEFAULT_RETRY_INTERVAL_SEC
    debug_log_interval_sec: float = DEFAULT_DEBUG_LOG_INTERVAL_SEC
    debug_dump_dir: Path = DEFAULT_DEBUG_DUMP_DIR

    def validate(self) -> "VoiceRuntimeConfig":
        """基础校验，尽早给出清晰错误信息。"""
        missing_paths = [
            path
            for path in (self.model_dir, self.model_path, self.tokens_path, self.vad_model_path)
            if not Path(path).exists()
        ]
        if missing_paths:
            missing = ", ".join(str(path) for path in missing_paths)
            raise FileNotFoundError(f"语音模型文件不存在: {missing}")

        if self.sample_rate <= 0:
            raise ValueError("sample_rate 必须大于 0")
        if self.channels <= 0:
            raise ValueError("channels 必须大于 0")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if self.cooldown_sec < 0:
            raise ValueError("cooldown_sec 不能小于 0")
        if self.min_speech_sec <= 0:
            raise ValueError("min_speech_sec 必须大于 0")
        if self.silence_sec <= 0:
            raise ValueError("silence_sec 必须大于 0")
        if self.max_speech_sec <= self.min_speech_sec:
            raise ValueError("max_speech_sec 必须大于 min_speech_sec")
        if not 0 < self.vad_threshold < 1:
            raise ValueError("vad_threshold 必须在 0 和 1 之间")
        if self.input_gain <= 0:
            raise ValueError("input_gain 必须大于 0")
        if self.asr_num_threads <= 0:
            raise ValueError("asr_num_threads 必须大于 0")
        if self.vad_buffer_sec <= 0:
            raise ValueError("vad_buffer_sec 必须大于 0")
        if self.retry_interval_sec <= 0:
            raise ValueError("retry_interval_sec 必须大于 0")
        if self.debug_log_interval_sec <= 0:
            raise ValueError("debug_log_interval_sec 必须大于 0")

        return self
