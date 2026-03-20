#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : override_state.py
@Author  : Z-Teddy
@Brief   : 主程序运行时语音 mode override 的轻量状态封装
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceOverrideSnapshot:
    active: bool = False
    mode: str = ""
    until: float = 0.0
    source: str = ""
    text: str = ""


class VoiceOverrideController:
    """维护当前语音 override 的生命周期。"""

    def __init__(self):
        self._snapshot = VoiceOverrideSnapshot()
        self._last_blocked_log_at = 0.0
        self._last_blocked_key = ("", "")

    def snapshot(self) -> VoiceOverrideSnapshot:
        return self._snapshot

    def is_active(self, now: float = None) -> bool:
        if not self._snapshot.active:
            return False
        now = time.monotonic() if now is None else now
        return self._snapshot.until > now

    def remaining_sec(self, now: float = None) -> float:
        if not self._snapshot.active:
            return 0.0
        now = time.monotonic() if now is None else now
        return max(0.0, self._snapshot.until - now)

    def current_mode(self, now: float = None) -> str:
        if not self.is_active(now):
            return ""
        return self._snapshot.mode

    def set(
        self,
        mode: str,
        duration_sec: float,
        *,
        source: str = "voice",
        text: str = "",
        now: float = None,
    ) -> VoiceOverrideSnapshot:
        now = time.monotonic() if now is None else now
        previous = self._snapshot
        duration_sec = max(0.0, float(duration_sec))
        self._snapshot = VoiceOverrideSnapshot(
            active=duration_sec > 0.0,
            mode=mode if duration_sec > 0.0 else "",
            until=now + duration_sec,
            source=source,
            text=text,
        )
        self._reset_blocked_log_window()
        return previous

    def clear(self) -> VoiceOverrideSnapshot:
        previous = self._snapshot
        self._snapshot = VoiceOverrideSnapshot()
        self._reset_blocked_log_window()
        return previous

    def expire_if_needed(self, now: float = None) -> VoiceOverrideSnapshot:
        if self.is_active(now):
            return VoiceOverrideSnapshot()

        if not self._snapshot.active:
            return VoiceOverrideSnapshot()

        return self.clear()

    def should_block(self, requested_mode: str, now: float = None) -> bool:
        active_mode = self.current_mode(now)
        return bool(active_mode) and requested_mode != active_mode

    def should_log_blocked(
        self,
        requested_mode: str,
        *,
        now: float = None,
        minimum_interval_sec: float = 0.5,
    ) -> bool:
        now = time.monotonic() if now is None else now
        current_mode = self.current_mode(now)
        key = (requested_mode, current_mode)
        if key != self._last_blocked_key:
            self._last_blocked_key = key
            self._last_blocked_log_at = now
            return True

        if now - self._last_blocked_log_at >= minimum_interval_sec:
            self._last_blocked_log_at = now
            return True

        return False

    def _reset_blocked_log_window(self) -> None:
        self._last_blocked_key = ("", "")
        self._last_blocked_log_at = 0.0
