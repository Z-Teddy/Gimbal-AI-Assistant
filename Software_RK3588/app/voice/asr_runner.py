#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : asr_runner.py
@Author  : Z-Teddy
@Brief   : SenseVoice 离线识别封装
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

try:
    import sherpa_onnx
except ImportError as exc:  # pragma: no cover - 依赖缺失时给出更清晰提示
    raise RuntimeError("未检测到 sherpa_onnx，请在 gimbal conda 环境中运行。") from exc

from app.voice.config import DEFAULT_SAMPLE_RATE, VoiceRuntimeConfig


def _ensure_model_paths(model_path: Path, tokens_path: Path) -> None:
    if not model_path.exists():
        raise FileNotFoundError(f"SenseVoice 模型不存在: {model_path}")
    if not tokens_path.exists():
        raise FileNotFoundError(f"SenseVoice tokens 文件不存在: {tokens_path}")


def _to_mono_float32(samples: Any) -> np.ndarray:
    waveform = np.asarray(samples, dtype=np.float32)
    if waveform.size == 0:
        return waveform.reshape(-1)

    if waveform.ndim == 1:
        return waveform

    if waveform.ndim == 2:
        if waveform.shape[0] <= 8 and waveform.shape[1] > waveform.shape[0]:
            waveform = waveform.mean(axis=0)
        else:
            waveform = waveform.mean(axis=1)
        return np.asarray(waveform, dtype=np.float32).reshape(-1)

    return waveform.reshape(-1)


@lru_cache(maxsize=1)
def _get_recognizer():
    runtime_config = VoiceRuntimeConfig().validate()
    model_path = Path(runtime_config.model_path)
    tokens_path = Path(runtime_config.tokens_path)
    _ensure_model_paths(model_path, tokens_path)

    return sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(model_path),
        tokens=str(tokens_path),
        num_threads=runtime_config.asr_num_threads,
        sample_rate=runtime_config.sample_rate,
        feature_dim=80,
        decoding_method="greedy_search",
        debug=False,
        provider="cpu",
        language="auto",
        use_itn=True,
    )


def decode_samples(samples, sample_rate: int) -> str:
    """
    对内存中的音频样本做离线识别。

    Args:
        samples: numpy 数组、list 或可转换为 numpy 的波形数据
        sample_rate (int): 当前样本采样率

    Returns:
        str: 识别文本
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate 必须大于 0")

    waveform = _to_mono_float32(samples)
    if waveform.size == 0:
        return ""

    recognizer = _get_recognizer()
    stream = recognizer.create_stream()
    stream.accept_waveform(int(sample_rate), waveform.tolist())
    recognizer.decode_stream(stream)
    return stream.result.text.strip()


def decode_wav(wav_path: str) -> str:
    """
    对 WAV 文件做离线识别。

    Args:
        wav_path (str): WAV 文件路径

    Returns:
        str: 识别文本
    """
    path = Path(wav_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"WAV 文件不存在: {path}")

    samples, sample_rate = sf.read(str(path), dtype="float32")
    return decode_samples(samples, int(sample_rate or DEFAULT_SAMPLE_RATE))
