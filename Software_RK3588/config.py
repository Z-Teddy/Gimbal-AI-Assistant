#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : config.py
@Author  : Z-Teddy
@Brief   : 全局配置兼容层 (基于 YAML 加载硬件参数、视觉参数与通信设置)
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from app.settings import load_settings


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR / "configs" / "default.yaml"

_ACTIVE_SETTINGS: Dict[str, Dict[str, Any]] = {}

CONFIG_PATH = str(DEFAULT_CONFIG_PATH)

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
CAM_INDEX = 0
CAM_WIDTH = 640
CAM_HEIGHT = 480
CAM_FLIP = 0
STM32_WIDTH = 319
STM32_HEIGHT = 239
SEND_INTERVAL = 0.04
RUNTIME_MODE = "gui"
WINDOW_NAME = "RK3588 AI Tracker"
RUNTIME_DISPLAY = ":0"
LOG_LEVEL = "INFO"
LOG_DIR = "logs"
LOG_FILE_NAME = "rk3588_tracker.log"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _normalize_path(config_path: Optional[str]) -> Path:
    if config_path is None:
        return DEFAULT_CONFIG_PATH

    path = Path(config_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _apply_settings(settings: Dict[str, Dict[str, Any]]) -> None:
    global _ACTIVE_SETTINGS
    global CONFIG_PATH
    global SERIAL_PORT, BAUD_RATE
    global CAM_INDEX, CAM_WIDTH, CAM_HEIGHT, CAM_FLIP
    global STM32_WIDTH, STM32_HEIGHT, SEND_INTERVAL
    global RUNTIME_MODE, WINDOW_NAME, RUNTIME_DISPLAY
    global LOG_LEVEL, LOG_DIR, LOG_FILE_NAME, LOG_FORMAT, LOG_DATE_FORMAT

    _ACTIVE_SETTINGS = deepcopy(settings)
    CONFIG_PATH = settings["_meta"]["config_path"]

    camera = settings["camera"]
    serial_cfg = settings["serial"]
    runtime = settings["runtime"]
    logging_cfg = settings["logging"]

    SERIAL_PORT = serial_cfg["port"]
    BAUD_RATE = int(serial_cfg["baud_rate"])

    CAM_INDEX = int(camera["index"])
    CAM_WIDTH = int(camera["width"])
    CAM_HEIGHT = int(camera["height"])
    CAM_FLIP = camera["flip"]

    STM32_WIDTH = int(serial_cfg["stm32_width"])
    STM32_HEIGHT = int(serial_cfg["stm32_height"])
    SEND_INTERVAL = float(serial_cfg["send_interval"])

    RUNTIME_MODE = runtime["mode"]
    WINDOW_NAME = runtime["window_name"]
    RUNTIME_DISPLAY = runtime["display"]

    LOG_LEVEL = logging_cfg["level"]
    LOG_DIR = logging_cfg["log_dir"]
    LOG_FILE_NAME = logging_cfg["file_name"]
    LOG_FORMAT = logging_cfg["format"]
    LOG_DATE_FORMAT = logging_cfg["date_format"]


def configure(config_path: Optional[str] = None, mode_override: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    加载 YAML 配置并同步到当前模块常量，供旧代码继续使用。

    Args:
        config_path (Optional[str], optional): 自定义 YAML 配置路径
        mode_override (Optional[str], optional): CLI 模式覆盖，支持 gui/headless

    Returns:
        Dict[str, Dict[str, Any]]: 当前生效的完整配置
    """
    settings = load_settings(_normalize_path(config_path))

    if mode_override is not None:
        if mode_override not in {"gui", "headless"}:
            raise ValueError("运行模式仅支持 'gui' 或 'headless'")
        settings["runtime"]["mode"] = mode_override

    _apply_settings(settings)
    return deepcopy(_ACTIVE_SETTINGS)


def get_settings() -> Dict[str, Dict[str, Any]]:
    """返回当前生效的完整配置副本"""
    return deepcopy(_ACTIVE_SETTINGS)


def get_logging_config() -> Dict[str, Any]:
    """返回当前 logging 配置副本"""
    return deepcopy(_ACTIVE_SETTINGS["logging"])


configure()
