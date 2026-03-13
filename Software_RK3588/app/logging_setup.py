#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : logging_setup.py
@Author  : Z-Teddy
@Brief   : 日志初始化模块
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import logging
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def setup_logging(logging_config: Mapping[str, Any]) -> Path:
    """
    初始化根日志器，并同时输出到控制台和 logs/ 文件。

    Args:
        logging_config (Mapping[str, Any]): logging 配置字典

    Returns:
        Path: 当前日志文件路径
    """
    level_name = str(logging_config.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    log_dir = Path(str(logging_config.get("log_dir", "logs")))
    if not log_dir.is_absolute():
        log_dir = PROJECT_ROOT / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    file_name = str(logging_config.get("file_name", "rk3588_tracker.log"))
    log_path = log_dir / file_name

    formatter = logging.Formatter(
        fmt=str(logging_config.get("format", "%(asctime)s | %(levelname)s | %(name)s | %(message)s")),
        datefmt=str(logging_config.get("date_format", "%Y-%m-%d %H:%M:%S")),
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return log_path
