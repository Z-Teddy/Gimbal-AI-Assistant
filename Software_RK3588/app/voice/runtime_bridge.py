#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : runtime_bridge.py
@Author  : Z-Teddy
@Brief   : 语音测试工具到 v3.0 主链路的薄桥接层
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import logging
import time
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Callable, Optional

import config
from app.camera_manager import CameraManager
from app.serial_ctrl import SerialController
from app.voice.command_parser import VoiceCommand
from app.voice.dispatcher import dispatch_command


@dataclass(frozen=True)
class RuntimeBridgeResult:
    action: str
    success: bool
    detail: str


@dataclass(frozen=True)
class VoiceRuntimeEvent:
    command: VoiceCommand
    text: str
    action: str
    queued_at: float
    segment_path: str = ""


@dataclass(frozen=True)
class VoiceRuntimeContext:
    update_mode: Callable[[str, str], bool]
    set_camera_enabled: Optional[Callable[[bool, str], bool]] = None
    set_last_voice_status: Optional[Callable[[str, str], None]] = None
    logger: Optional[logging.Logger] = None


class VoiceCommandBridge:
    """主程序集成版桥接：语音线程只入队，主线程轮询并执行。"""

    def __init__(self):
        self._queue: Queue = Queue()

    def enqueue_voice_command(
        self,
        command: VoiceCommand,
        *,
        text: str = "",
        action: str = "",
        segment_path: str = "",
    ) -> bool:
        if command == VoiceCommand.UNKNOWN:
            return False

        self._queue.put(
            VoiceRuntimeEvent(
                command=command,
                text=text,
                action=action or dispatch_command(command),
                queued_at=time.monotonic(),
                segment_path=segment_path,
            )
        )
        return True

    def enqueue_result(self, result) -> bool:
        if result is None or result.suppressed or result.raw_action == "noop":
            return False

        return self.enqueue_voice_command(
            result.command,
            text=result.text,
            action=result.raw_action,
            segment_path=getattr(result, "segment_path", ""),
        )

    def poll_voice_commands(self, max_commands: int = 8):
        events = []
        while len(events) < max_commands:
            try:
                events.append(self._queue.get_nowait())
            except Empty:
                break
        return events


def apply_voice_command_to_runtime(
    event_or_command,
    runtime_context: VoiceRuntimeContext,
) -> RuntimeBridgeResult:
    """将语音命令应用到当前主程序已持有的 runtime 对象。"""
    if isinstance(event_or_command, VoiceRuntimeEvent):
        event = event_or_command
        command = event.command
        text = event.text
    else:
        command = event_or_command
        text = ""
        event = VoiceRuntimeEvent(
            command=command,
            text="",
            action=dispatch_command(command),
            queued_at=time.monotonic(),
        )

    action = dispatch_command(command)
    reason = f"voice:{command.value}"
    if text:
        reason = f"{reason} text={text}"

    if runtime_context.set_last_voice_status is not None:
        runtime_context.set_last_voice_status(command.value, text)

    if command == VoiceCommand.TRACK:
        changed = runtime_context.update_mode("track", reason)
        return RuntimeBridgeResult(action=action, success=True, detail=f"mode track changed={changed}")

    if command == VoiceCommand.HOLD:
        changed = runtime_context.update_mode("hold", reason)
        return RuntimeBridgeResult(action=action, success=True, detail=f"mode hold changed={changed}")

    if command == VoiceCommand.SCAN:
        changed = runtime_context.update_mode("scan", reason)
        return RuntimeBridgeResult(action=action, success=True, detail=f"mode scan changed={changed}")

    if command == VoiceCommand.HOME:
        changed = runtime_context.update_mode("return_home", reason)
        return RuntimeBridgeResult(
            action=action,
            success=True,
            detail=f"mode return_home changed={changed}",
        )

    if command == VoiceCommand.OPEN_CAMERA:
        if runtime_context.set_camera_enabled is None:
            return RuntimeBridgeResult(action=action, success=False, detail="camera toggle unavailable")
        changed = runtime_context.set_camera_enabled(True, reason)
        return RuntimeBridgeResult(action=action, success=True, detail=f"camera open changed={changed}")

    if command == VoiceCommand.CLOSE_CAMERA:
        if runtime_context.set_camera_enabled is None:
            return RuntimeBridgeResult(action=action, success=False, detail="camera toggle unavailable")
        changed = runtime_context.set_camera_enabled(False, reason)
        return RuntimeBridgeResult(action=action, success=True, detail=f"camera close changed={changed}")

    logger = runtime_context.logger
    if logger is not None:
        logger.debug("忽略未知语音命令: %s", event)
    return RuntimeBridgeResult(action=action, success=True, detail="noop")


class VoiceRuntimeBridge:
    """
    复用当前仓库已有 camera / protocol / serial 主链路。

    目标是让语音测试工具具备真实动作执行能力，而不去大改 main.py。
    """

    _MODE_MAP = {
        VoiceCommand.TRACK: "track",
        VoiceCommand.HOLD: "hold",
        VoiceCommand.SCAN: "scan",
        VoiceCommand.HOME: "return_home",
    }

    def __init__(self):
        config.configure()
        self.logger = logging.getLogger(__name__)
        self._serial: Optional[SerialController] = None
        self._camera: Optional[CameraManager] = None

    def execute(self, command: VoiceCommand) -> RuntimeBridgeResult:
        action = dispatch_command(command)

        if command in self._MODE_MAP:
            return self._execute_mode(command, action)

        if command == VoiceCommand.OPEN_CAMERA:
            return self._open_camera(action)

        if command == VoiceCommand.CLOSE_CAMERA:
            return self._close_camera(action)

        return RuntimeBridgeResult(action=action, success=True, detail="noop")

    def close(self) -> None:
        if self._camera is not None:
            self._camera.close()
            self._camera = None

        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def _ensure_serial(self) -> SerialController:
        if self._serial is None:
            self._serial = SerialController()

        # 测试工具要显式下发模式命令，这里只开启实例级开关，不改全局主程序。
        self._serial.mode_command_enabled = True
        return self._serial

    def _execute_mode(self, command: VoiceCommand, action: str) -> RuntimeBridgeResult:
        serial_ctrl = self._ensure_serial()
        serial_ctrl.try_reconnect()
        mode_name = self._MODE_MAP[command]
        ok = serial_ctrl.send_mode(mode_name, force=True)

        if ok:
            return RuntimeBridgeResult(
                action=action,
                success=True,
                detail=f"mode sent via SerialController.send_mode({mode_name!r})",
            )

        return RuntimeBridgeResult(
            action=action,
            success=False,
            detail="mode send skipped or serial unavailable",
        )

    def _open_camera(self, action: str) -> RuntimeBridgeResult:
        if self._camera is not None:
            self._camera.close()
            self._camera = None

        self._camera = CameraManager()
        opened = (
            self._camera.cap is not None
            and hasattr(self._camera.cap, "isOpened")
            and self._camera.cap.isOpened()
        )

        if opened:
            return RuntimeBridgeResult(action=action, success=True, detail="camera opened")

        return RuntimeBridgeResult(action=action, success=False, detail="camera open failed")

    def _close_camera(self, action: str) -> RuntimeBridgeResult:
        if self._camera is None:
            return RuntimeBridgeResult(action=action, success=True, detail="camera already closed")

        self._camera.close()
        self._camera = None
        return RuntimeBridgeResult(action=action, success=True, detail="camera closed")
