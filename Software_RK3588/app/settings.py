#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : settings.py
@Author  : Z-Teddy
@Brief   : YAML 配置加载与基础校验
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import yaml


DEFAULT_SETTINGS: Dict[str, Dict[str, Any]] = {
    "camera": {
        "index": 0,
        "width": 640,
        "height": 480,
        "flip": 0,
        "max_read_failures": 5,
        "reconnect_interval_sec": 2.0,
    },
    "serial": {
        "port": "/dev/ttyUSB0",
        "baud_rate": 115200,
        "stm32_width": 319,
        "stm32_height": 239,
        "send_interval": 0.04,
        "reconnect_interval_sec": 2.0,
    },
    "detector": {
        "type": "haar_face",
    },
    "protocol": {
        "heartbeat_enabled": False,
        "heartbeat_interval_sec": 1.0,
        "no_target_enabled": False,
        "no_target_interval_sec": 0.2,
        "mode_command_enabled": False,
    },
    "control": {
        "default_mode": "track",
        "target_lost_timeout_sec": 0.3,
        "lost_confirm_frames": 2,
        "reacquire_confirm_frames": 2,
        "no_target_mode": "hold",
        "return_home_after_sec": 0.0,
        "home_x": 320,
        "home_y": 240,
        "scan_enabled": False,
        "scan_interval_sec": 1.0,
    },
    "runtime": {
        "mode": "gui",
        "window_name": "RK3588 AI Tracker",
        "display": ":0",
    },
    "logging": {
        "level": "INFO",
        "log_dir": "logs",
        "file_name": "rk3588_tracker.log",
        "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
    },
}


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _require_dict(settings: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = settings.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"配置项 '{key}' 必须是对象")
    return value


def _require_int(section: Dict[str, Any], key: str, *, minimum: int = None) -> int:
    value = section.get(key)
    if not isinstance(value, int):
        raise ValueError(f"配置项 '{key}' 必须是整数")
    if minimum is not None and value < minimum:
        raise ValueError(f"配置项 '{key}' 必须大于等于 {minimum}")
    return value


def _require_number(section: Dict[str, Any], key: str, *, minimum: float = None) -> float:
    value = section.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"配置项 '{key}' 必须是数字")
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError(f"配置项 '{key}' 必须大于等于 {minimum}")
    return value


def _require_str(section: Dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"配置项 '{key}' 必须是非空字符串")
    return value


def _require_positive_number(section: Dict[str, Any], key: str) -> float:
    value = section.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"配置项 '{key}' 必须是数字")
    value = float(value)
    if value <= 0:
        raise ValueError(f"配置项 '{key}' 必须大于 0")
    return value


def _require_bool(section: Dict[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"配置项 '{key}' 必须是布尔值")
    return value


def _validate_settings(settings: Dict[str, Any]) -> None:
    camera = _require_dict(settings, "camera")
    serial = _require_dict(settings, "serial")
    detector = _require_dict(settings, "detector")
    protocol = _require_dict(settings, "protocol")
    control = _require_dict(settings, "control")
    runtime = _require_dict(settings, "runtime")
    logging_cfg = _require_dict(settings, "logging")

    _require_int(camera, "index", minimum=0)
    _require_int(camera, "width", minimum=1)
    _require_int(camera, "height", minimum=1)
    if camera.get("flip") not in (-1, 0, 1, None):
        raise ValueError("配置项 'camera.flip' 必须是 -1、0、1 或 null")
    _require_int(camera, "max_read_failures", minimum=1)
    _require_positive_number(camera, "reconnect_interval_sec")

    _require_str(serial, "port")
    _require_int(serial, "baud_rate", minimum=1)
    _require_int(serial, "stm32_width", minimum=1)
    _require_int(serial, "stm32_height", minimum=1)
    _require_number(serial, "send_interval", minimum=0.0)
    _require_positive_number(serial, "reconnect_interval_sec")

    _require_str(detector, "type")

    _require_bool(protocol, "heartbeat_enabled")
    _require_positive_number(protocol, "heartbeat_interval_sec")
    _require_bool(protocol, "no_target_enabled")
    _require_positive_number(protocol, "no_target_interval_sec")
    _require_bool(protocol, "mode_command_enabled")

    if control.get("default_mode") not in {"track", "hold", "return_home", "scan"}:
        raise ValueError(
            "配置项 'control.default_mode' 仅支持 'track'、'hold'、'return_home' 或 'scan'"
        )
    _require_number(control, "target_lost_timeout_sec", minimum=0.0)
    _require_int(control, "lost_confirm_frames", minimum=1)
    _require_int(control, "reacquire_confirm_frames", minimum=1)
    if control.get("no_target_mode") not in {"hold", "return_home", "scan"}:
        raise ValueError(
            "配置项 'control.no_target_mode' 仅支持 'hold'、'return_home' 或 'scan'"
        )
    _require_number(control, "return_home_after_sec", minimum=0.0)
    _require_int(control, "home_x", minimum=0)
    _require_int(control, "home_y", minimum=0)
    _require_bool(control, "scan_enabled")
    _require_positive_number(control, "scan_interval_sec")

    if runtime.get("mode") not in {"gui", "headless"}:
        raise ValueError("配置项 'runtime.mode' 仅支持 'gui' 或 'headless'")
    _require_str(runtime, "window_name")
    display = runtime.get("display")
    if display is not None and not isinstance(display, str):
        raise ValueError("配置项 'runtime.display' 必须是字符串或 null")

    _require_str(logging_cfg, "level")
    _require_str(logging_cfg, "log_dir")
    _require_str(logging_cfg, "file_name")
    _require_str(logging_cfg, "format")
    _require_str(logging_cfg, "date_format")


def load_settings(config_path: Path) -> Dict[str, Any]:
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        raise ValueError("YAML 根节点必须是对象")

    settings = _deep_merge(DEFAULT_SETTINGS, loaded)
    _validate_settings(settings)
    settings["_meta"] = {
        "config_path": str(config_path.resolve()),
    }
    return settings
