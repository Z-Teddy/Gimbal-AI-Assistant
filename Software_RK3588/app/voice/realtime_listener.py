#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : realtime_listener.py
@Author  : Z-Teddy
@Brief   : USB 麦克风实时监听与命令识别
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import logging
import re
import subprocess
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import soundfile as sf

try:
    import sherpa_onnx
except ImportError as exc:  # pragma: no cover - 依赖缺失时给出更清晰提示
    raise RuntimeError("未检测到 sherpa_onnx，请在 gimbal conda 环境中运行。") from exc

from app.voice.asr_runner import decode_samples
from app.voice.command_parser import VoiceCommand, parse_command
from app.voice.config import DEFAULT_RECORD_DEVICE_KEYWORD, VoiceRuntimeConfig
from app.voice.dispatcher import dispatch_command


_CARD_LINE_RE = re.compile(r"^card\s+(\d+):")


class AudioDeviceNotFoundError(RuntimeError):
    """未找到指定录音设备。"""


@dataclass(frozen=True)
class VoiceRecognitionResult:
    text: str
    command: VoiceCommand
    action: str
    raw_action: str
    speech_duration_sec: float
    device: str = ""
    suppressed: bool = False
    segment_path: str = ""


class VoiceRealtimeListener:
    """
    常驻监听 USB 麦克风，检测语音段并输出命令识别结果。

    设计上保持独立，后续可以在主程序中将 run_forever() 放入单独线程。
    状态机流转为: idle -> speech_started -> buffering -> speech_end -> decode -> cooldown。
    """

    def __init__(
        self,
        runtime_config: Optional[VoiceRuntimeConfig] = None,
        *,
        device_keyword: Optional[str] = None,
        cooldown_sec: Optional[float] = None,
        debug: bool = False,
    ):
        config = runtime_config or VoiceRuntimeConfig()
        if device_keyword is not None:
            config = replace(config, record_device_keyword=device_keyword)
        if cooldown_sec is not None:
            config = replace(config, cooldown_sec=float(cooldown_sec))

        self.config = config.validate()
        self.debug = bool(debug)
        self.logger = logging.getLogger(__name__)
        self._stop_event = threading.Event()
        self._recorder_process = None
        self._vad_window_size = 512
        self._vad = self._create_vad()
        self._state = "idle"
        self._speech_detected = False
        self._last_action = ""
        self._last_action_at = 0.0
        self._chunk_count = 0
        self._window_count = 0
        self._total_bytes = 0
        self._last_chunk_log_at = 0.0
        self._pcm_remainder = b""
        self._vad_input_buffer = np.empty((0,), dtype=np.float32)
        self._segment_index = 0
        self._debug_dump_dir = Path(self.config.debug_dump_dir)
        if self.debug:
            self._debug_dump_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def resolve_record_device(keyword: str = DEFAULT_RECORD_DEVICE_KEYWORD) -> str:
        """从 `arecord -l` 输出中解析 USB 麦克风卡号。"""
        try:
            result = subprocess.run(
                ["arecord", "-l"],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("未找到 arecord，请确认系统已安装 ALSA 录音工具。") from exc

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(f"`arecord -l` 执行失败: {stderr or 'unknown error'}")

        for line in result.stdout.splitlines():
            if keyword not in line:
                continue

            match = _CARD_LINE_RE.search(line.strip())
            if not match:
                raise RuntimeError(f"匹配到了 USB 麦克风，但无法解析 card 编号: {line.strip()}")

            card_index = match.group(1)
            return f"plughw:{card_index},0"

        raise AudioDeviceNotFoundError(
            f"未检测到 USB 麦克风，关键字={keyword!r}。请先执行 `arecord -l` 确认设备是否存在。"
        )

    def stop(self) -> None:
        """请求停止监听。"""
        self._stop_event.set()
        self._stop_recorder()

    def process_segment_samples(
        self,
        samples,
        *,
        sample_rate: Optional[int] = None,
        device: str = "",
    ) -> Optional[VoiceRecognitionResult]:
        """对完整语音段执行 ASR -> 命令解析 -> 动作派发。"""
        rate = int(sample_rate or self.config.sample_rate)
        waveform = np.asarray(samples, dtype=np.float32).reshape(-1)
        if waveform.size == 0:
            return None

        speech_duration_sec = waveform.size / float(rate)
        if speech_duration_sec < self.config.min_speech_sec:
            if self.debug:
                self.logger.debug("忽略过短语音段: %.3fs", speech_duration_sec)
            return None

        try:
            text = decode_samples(waveform, rate).strip()
        except Exception as exc:
            self.logger.exception("ASR 识别失败: %s", exc)
            return None

        if not text:
            if self.debug:
                self.logger.debug("ASR 结果为空，忽略本次语音段。")
            return None

        command = parse_command(text)
        raw_action = dispatch_command(command)
        segment_path = self._dump_debug_segment(waveform, rate) if self.debug else ""

        suppressed = False
        final_action = raw_action
        if self._should_suppress(raw_action):
            suppressed = True
            final_action = f"noop (cooldown:{raw_action})"
            self._set_state("cooldown")
        elif raw_action != "noop":
            self._last_action = raw_action
            self._last_action_at = time.monotonic()

        result = VoiceRecognitionResult(
            text=text,
            command=command,
            action=final_action,
            raw_action=raw_action,
            speech_duration_sec=speech_duration_sec,
            device=device,
            suppressed=suppressed,
            segment_path=segment_path,
        )

        log_method = self.logger.info
        if command == VoiceCommand.UNKNOWN:
            log_method = self.logger.warning

        log_method(
            "语音识别完成: text=%s cmd=%s action=%s suppressed=%s duration=%.2fs",
            result.text,
            result.command.value,
            result.action,
            result.suppressed,
            result.speech_duration_sec,
        )
        if self.debug and result.segment_path:
            self.logger.debug("voice_segment=%s", result.segment_path)

        return result

    def run_forever(
        self,
        on_result: Optional[Callable[[VoiceRecognitionResult], None]] = None,
    ) -> None:
        """常驻监听，直到收到 stop() 或 Ctrl+C。"""
        result_handler = on_result or self._print_result

        while not self._stop_event.is_set():
            try:
                device = self.resolve_record_device(self.config.record_device_keyword)
                self.logger.info(
                    "语音监听启动: device=%s keyword=%s",
                    device,
                    self.config.record_device_keyword,
                )
                self._run_recorder_session(device, result_handler)
            except KeyboardInterrupt:
                raise
            except AudioDeviceNotFoundError as exc:
                self.logger.error("%s", exc)
            except Exception as exc:
                self.logger.exception("语音监听异常: %s", exc)
            finally:
                self._stop_recorder()
                self._reset_vad()

            if self._stop_event.wait(self.config.retry_interval_sec):
                break

    def _create_vad(self):
        vad_config = sherpa_onnx.VadModelConfig()
        vad_config.sample_rate = self.config.sample_rate
        vad_config.num_threads = 1
        vad_config.provider = "cpu"
        vad_config.debug = self.debug
        vad_config.silero_vad.model = str(Path(self.config.vad_model_path))
        vad_config.silero_vad.threshold = self.config.vad_threshold
        vad_config.silero_vad.min_speech_duration = self.config.min_speech_sec
        vad_config.silero_vad.min_silence_duration = self.config.silence_sec
        vad_config.silero_vad.max_speech_duration = self.config.max_speech_sec
        self._vad_window_size = int(vad_config.silero_vad.window_size)
        return sherpa_onnx.VoiceActivityDetector(vad_config, self.config.vad_buffer_sec)

    def _run_recorder_session(
        self,
        device: str,
        result_handler: Callable[[VoiceRecognitionResult], None],
    ) -> None:
        self._reset_vad()
        process = self._start_recorder(device)
        self._recorder_process = process
        bytes_per_chunk = self.config.chunk_size * self.config.channels * 2
        self._chunk_count = 0
        self._window_count = 0
        self._total_bytes = 0
        self._last_chunk_log_at = 0.0
        self._pcm_remainder = b""
        self._vad_input_buffer = np.empty((0,), dtype=np.float32)

        if self.debug:
            self.logger.debug(
                "录音命令已启动: chunk=%s sample_rate=%s channels=%s vad_window=%s vad_threshold=%.2f input_gain=%.1fx min_speech=%.2fs max_speech=%.2fs silence=%.2fs",
                self.config.chunk_size,
                self.config.sample_rate,
                self.config.channels,
                self._vad_window_size,
                self.config.vad_threshold,
                self.config.input_gain,
                self.config.min_speech_sec,
                self.config.max_speech_sec,
                self.config.silence_sec,
            )

        while not self._stop_event.is_set():
            if process.stdout is None:
                raise RuntimeError("arecord stdout 未正确打开")

            raw_bytes = process.stdout.read(bytes_per_chunk)
            if not raw_bytes:
                break
            self._chunk_count += 1
            self._total_bytes += len(raw_bytes)

            samples = self._decode_pcm_chunk(raw_bytes)
            if samples.size == 0:
                self._maybe_log_chunk_stats(len(raw_bytes), 0.0, 0.0)
                continue

            try:
                rms = float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0
                peak = float(np.max(np.abs(samples))) if samples.size else 0.0
                self._consume_chunk(samples, device, result_handler)
                self._maybe_log_chunk_stats(len(raw_bytes), rms, peak)
            except Exception as exc:
                self.logger.exception("音频处理异常，已重置当前 VAD 状态: %s", exc)
                self._reset_vad()

        self._flush_pending_segments(device, result_handler)

        if self._stop_event.is_set():
            return

        returncode = process.poll()
        stderr_text = self._read_stderr(process) if returncode is not None else ""
        if returncode not in (0, None):
            self.logger.warning(
                "录音进程退出: returncode=%s detail=%s",
                returncode,
                stderr_text or "unknown error",
            )
        elif stderr_text and self.debug:
            self.logger.debug("arecord: %s", stderr_text)

    def _consume_chunk(
        self,
        samples: np.ndarray,
        device: str,
        result_handler: Callable[[VoiceRecognitionResult], None],
    ) -> None:
        # 这里按块推进一个简单状态机:
        # idle -> speech_started -> buffering -> speech_end -> decode -> cooldown
        if self._vad_input_buffer.size == 0:
            buffered = np.asarray(samples, dtype=np.float32)
        else:
            buffered = np.concatenate((self._vad_input_buffer, np.asarray(samples, dtype=np.float32)))

        offset = 0
        while offset + self._vad_window_size <= buffered.size:
            window = buffered[offset : offset + self._vad_window_size]
            self._window_count += 1
            self._consume_vad_window(window, device, result_handler)
            offset += self._vad_window_size

        self._vad_input_buffer = buffered[offset:]

    def _consume_vad_window(
        self,
        window: np.ndarray,
        device: str,
        result_handler: Callable[[VoiceRecognitionResult], None],
    ) -> None:
        was_speech_detected = self._speech_detected
        self._vad.accept_waveform(window.tolist())
        is_speech_detected = bool(self._vad.is_speech_detected())

        if not was_speech_detected and is_speech_detected:
            self._set_state("speech_started")
        elif is_speech_detected:
            self._set_state("buffering")
        elif was_speech_detected and not is_speech_detected:
            self._set_state("speech_end")

        self._speech_detected = is_speech_detected
        self._drain_ready_segments(device, result_handler)

        if not self._speech_detected and self._state not in {"decode", "cooldown"}:
            self._set_state("idle")

    def _drain_ready_segments(
        self,
        device: str,
        result_handler: Callable[[VoiceRecognitionResult], None],
    ) -> None:
        while not self._vad.empty():
            self._set_state("decode")
            segment = self._vad.front
            segment_samples = np.asarray(segment.samples, dtype=np.float32).copy()
            self._vad.pop()

            result = self.process_segment_samples(
                segment_samples,
                sample_rate=self.config.sample_rate,
                device=device,
            )
            if result is not None:
                result_handler(result)

        if not self._speech_detected:
            self._set_state("idle")

    def _flush_pending_segments(
        self,
        device: str,
        result_handler: Callable[[VoiceRecognitionResult], None],
    ) -> None:
        try:
            if self._vad_input_buffer.size > 0:
                self._vad.accept_waveform(self._vad_input_buffer.tolist())
                self._vad_input_buffer = np.empty((0,), dtype=np.float32)
            self._vad.flush()
            self._speech_detected = False
            self._drain_ready_segments(device, result_handler)
        except Exception as exc:
            self.logger.exception("刷新 VAD 缓冲失败: %s", exc)
        finally:
            self._reset_vad()

    def _reset_vad(self) -> None:
        self._vad.reset()
        self._speech_detected = False
        self._vad_input_buffer = np.empty((0,), dtype=np.float32)
        self._pcm_remainder = b""
        self._set_state("idle")

    def _should_suppress(self, raw_action: str) -> bool:
        if raw_action == "noop":
            return False

        return (
            self._last_action == raw_action
            and time.monotonic() - self._last_action_at < self.config.cooldown_sec
        )

    def _start_recorder(self, device: str):
        try:
            return subprocess.Popen(
                [
                    "arecord",
                    "-q",
                    "-D",
                    device,
                    "-f",
                    "S16_LE",
                    "-r",
                    str(self.config.sample_rate),
                    "-c",
                    str(self.config.channels),
                    "-t",
                    "raw",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("未找到 arecord，请确认系统已安装 ALSA 录音工具。") from exc

    def _stop_recorder(self) -> None:
        process = self._recorder_process
        self._recorder_process = None
        if process is None:
            return

        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1.0)

        self._read_stderr(process)

    def _decode_pcm_chunk(self, raw_bytes: bytes) -> np.ndarray:
        if self._pcm_remainder:
            raw_bytes = self._pcm_remainder + raw_bytes
            self._pcm_remainder = b""

        if len(raw_bytes) % 2 != 0:
            self._pcm_remainder = raw_bytes[-1:]
            raw_bytes = raw_bytes[:-1]

        pcm = np.frombuffer(raw_bytes, dtype=np.int16)
        if pcm.size == 0:
            return np.empty((0,), dtype=np.float32)

        samples = pcm.astype(np.float32) / 32768.0
        if samples.size == 0:
            return samples

        # 去掉轻微直流偏置，再做软件增益，帮助低电平 USB 麦克风更容易触发 VAD。
        samples = samples - float(np.mean(samples))
        if self.config.input_gain != 1.0:
            samples = np.clip(samples * float(self.config.input_gain), -1.0, 1.0)
        return samples.astype(np.float32, copy=False)

    @staticmethod
    def _read_stderr(process) -> str:
        if process is None or process.stderr is None:
            return ""
        try:
            data = process.stderr.read()
        except Exception:
            return ""
        return data.decode("utf-8", errors="ignore").strip()

    def _set_state(self, state: str) -> None:
        if state == self._state:
            return
        if self.debug:
            self.logger.debug("voice_state=%s", state)
        self._state = state

    def _maybe_log_chunk_stats(self, bytes_read: int, rms: float, peak: float) -> None:
        if not self.debug:
            return

        now = time.monotonic()
        if now - self._last_chunk_log_at < self.config.debug_log_interval_sec:
            return

        self._last_chunk_log_at = now
        self.logger.debug(
            "audio_chunk chunk_count=%s window_count=%s bytes_read=%s total_bytes=%s rms=%.5f peak=%.5f is_speech_detected=%s state=%s",
            self._chunk_count,
            self._window_count,
            bytes_read,
            self._total_bytes,
            rms,
            peak,
            self._speech_detected,
            self._state,
        )

    def _dump_debug_segment(self, samples: np.ndarray, sample_rate: int) -> str:
        self._segment_index += 1
        segment_path = self._debug_dump_dir / f"segment_{self._segment_index:04d}.wav"
        try:
            sf.write(str(segment_path), samples, sample_rate)
            self.logger.debug("segment_dump=%s", segment_path)
            return str(segment_path)
        except Exception as exc:
            self.logger.warning("保存调试语音段失败: %s", exc)
            return ""

    @staticmethod
    def _print_result(result: VoiceRecognitionResult) -> None:
        print(f"ASR: {result.text}", flush=True)
        print(f"CMD: {result.command.value}", flush=True)
        print(f"ACTION: {result.action}", flush=True)
        print("", flush=True)
