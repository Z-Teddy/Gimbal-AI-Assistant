#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : vision.py
@Author  : Z-Teddy
@Brief   : 视觉检测兼容层
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

from app.detectors import DetectionResult, HaarFaceDetector


class FaceDetector(HaarFaceDetector):
    """
    向后兼容旧接口，保留 process_frame -> (frame, target) 返回形式。
    """

    def process_frame(self, frame):
        result = self.detect(frame)
        return result.annotated_frame, result.target_center


__all__ = ["DetectionResult", "FaceDetector", "HaarFaceDetector"]
