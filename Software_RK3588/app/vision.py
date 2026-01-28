#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : vision.py
@Author  : Z-Teddy
@Brief   : 视觉检测模块 (基于 OpenCV Haar Cascade)
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import cv2
import config

class FaceDetector:
    """
    人脸检测与追踪处理类

    基于 OpenCV 经典的 Haar 级联分类器实现，
    负责处理视频帧、检测人脸并计算最大目标的中心坐标。
    """

    def __init__(self):
        """
        初始化检测器
        
        加载 OpenCV 内置的 Haar 级联人脸模型文件。
        """
        # 加载 OpenCV 自带的人脸检测模型
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        print("[Vision] FaceDetector 初始化完成")

    def process_frame(self, frame):
        """
        处理单帧图像进行人脸检测与追踪

        处理流程:
        1. 图像预处理 (翻转、灰度化)
        2. Haar 特征检测
        3. 筛选最大目标 (避免多目标干扰，锁定最近的人脸)
        4. 绘制可视化元素 (边框、中心点、状态文本)

        Args:
            frame (numpy.ndarray): 原始视频帧 (BGR 格式)

        Returns:
            tuple: (处理后的图像 frame, 目标中心坐标 target_center)
                   - frame: 绘制了辅助信息的图像
                   - target_center: (cx, cy) 元组，未检测到时为 None
        """
        # 1. 图像预处理: 画面翻转 (根据 config.py 配置)
        if config.CAM_FLIP is not None:
            frame = cv2.flip(frame, config.CAM_FLIP)

        # 2. 颜色空间转换: BGR -> Gray (Haar 级联分类器仅支持灰度图)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 3. 多尺度人脸检测 (Multi-scale Detection)
        # scaleFactor=1.1: 每次图像缩放比例 (越小越慢但越细致)
        # minNeighbors=4: 每个候选矩形至少保留的邻居数 (越大误检越少)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 6)

        target_center = None
        max_area = 0

        # 4. 目标筛选: 寻找最大面积的人脸 (Priority: Largest Area)
        # 策略: 假设画面中最大的人脸是我们需要追踪的主目标
        for (x, y, w, h) in faces:
            # 绘制人脸矩形框 (Green)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # 计算面积
            area = w * h
            
            # 更新最大目标
            if area > max_area:
                max_area = area
                # 计算中心点坐标
                cx = x + w // 2
                cy = y + h // 2
                target_center = (cx, cy)

        # 5. 可视化反馈 (Visual Feedback)
        if target_center:
            # 检测到目标: 画红色中心点并显示坐标
            cv2.circle(frame, target_center, 5, (0, 0, 255), -1)
            cv2.putText(frame, f"Target: {target_center}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            # 未检测到目标: 显示扫描状态
            cv2.putText(frame, "Scanning...", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

        return frame, target_center