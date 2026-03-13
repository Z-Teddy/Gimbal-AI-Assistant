#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : camera_manager.py
@Author  : Z-Teddy
@Brief   : 摄像头管理模块 (打开、读帧、自动恢复)
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import logging
import time

import cv2

import config


class CameraManager:
    """
    摄像头管理器

    负责摄像头初始化、单帧读取、连续失败计数、
    达到阈值后的释放与定时重连。
    """

    def __init__(self):
        camera_cfg = config.get_settings().get("camera", {})

        self.logger = logging.getLogger(__name__)
        self.index = int(camera_cfg.get("index", config.CAM_INDEX))
        self.width = int(camera_cfg.get("width", config.CAM_WIDTH))
        self.height = int(camera_cfg.get("height", config.CAM_HEIGHT))
        self.max_read_failures = max(1, int(camera_cfg.get("max_read_failures", 5)))
        self.reconnect_interval_sec = max(
            0.1,
            float(camera_cfg.get("reconnect_interval_sec", 2.0)),
        )

        self.cap = None
        self.read_failures = 0
        self.next_reconnect_time = 0.0

        self._open_camera(reconnect=False)

    def _configure_capture(self, capture):
        """配置摄像头基础参数"""
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

    def _open_camera(self, reconnect: bool):
        """打开摄像头，支持首次打开与重连日志区分"""
        if reconnect:
            self.logger.info("尝试重新打开摄像头 index=%s...", self.index)
        else:
            self.logger.info("正在打开摄像头 index=%s...", self.index)

        capture = cv2.VideoCapture(self.index)
        self._configure_capture(capture)

        if capture.isOpened():
            self.cap = capture
            self.read_failures = 0
            self.next_reconnect_time = 0.0
            if reconnect:
                self.logger.info("摄像头重连成功")
            else:
                self.logger.info("摄像头首次打开成功")
            return True

        capture.release()
        self.cap = None
        self.next_reconnect_time = time.monotonic() + self.reconnect_interval_sec

        if reconnect:
            self.logger.warning(
                "摄像头重连失败，将在 %.2f 秒后继续尝试",
                self.reconnect_interval_sec,
            )
        else:
            self.logger.warning(
                "摄像头首次打开失败，将在 %.2f 秒后自动重试",
                self.reconnect_interval_sec,
            )
        return False

    def _release_capture(self, reason: str):
        """释放当前摄像头资源"""
        if self.cap is not None:
            self.logger.warning("释放当前摄像头: %s", reason)
            self.cap.release()
            self.cap = None

    def _mark_read_failure(self, reason: str):
        """记录单次读帧失败，并在达到阈值后进入重连流程"""
        self.read_failures += 1
        self.logger.warning(
            "摄像头读帧失败 (%s/%s): %s",
            self.read_failures,
            self.max_read_failures,
            reason,
        )

        if self.read_failures < self.max_read_failures:
            return

        self.logger.error(
            "摄像头连续读帧失败达到阈值 %s，准备释放并重连",
            self.max_read_failures,
        )
        self._release_capture("连续读帧失败达到阈值")
        self.read_failures = 0
        self.next_reconnect_time = time.monotonic() + self.reconnect_interval_sec

    def read_frame(self):
        """
        读取单帧图像。

        Returns:
            numpy.ndarray | None: 读取成功返回 frame，否则返回 None
        """
        if self.cap is None:
            now = time.monotonic()
            if now < self.next_reconnect_time:
                time.sleep(min(0.05, self.next_reconnect_time - now))
                return None

            self._open_camera(reconnect=True)
            if self.cap is None:
                return None

        if not self.cap.isOpened():
            self._mark_read_failure("摄像头句柄未处于打开状态")
            return None

        ret, frame = self.cap.read()
        if ret:
            if self.read_failures > 0:
                self.logger.info("摄像头读帧恢复，连续失败计数已清零")
            self.read_failures = 0
            return frame

        self._mark_read_failure("cv2.VideoCapture.read() 返回失败")
        return None

    def close(self):
        """关闭摄像头资源"""
        if self.cap is not None:
            self.logger.info("关闭摄像头资源")
            self.cap.release()
            self.cap = None
