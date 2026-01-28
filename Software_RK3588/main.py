#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : main.py
@Author  : Z-Teddy
@Brief   : 主程序入口 (RK3588 视觉追踪与云台控制)
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import os
# [Environment Config]
# 强制指定显示输出到本地 HDMI 屏幕 (:0)
os.environ["DISPLAY"] = ":0"

import cv2
import config
from app.vision import FaceDetector
from app.serial_ctrl import SerialController

def main():
    """
    系统主循环
    
    流程:
    1. 初始化视觉与通信模块
    2. 打开摄像头并配置分辨率
    3. 进入实时处理循环:
       - 读取视频帧
       - 人脸检测 (Haar)
       - 串口发送坐标 (Protocol)
       - 本地 HDMI 显示
    4. 资源释放与退出
    """
    print("=== RK3588 异构云台追踪系统启动 ===")
    
    # 1. [System Init] 实例化核心功能模块
    tracker = FaceDetector()
    comm = SerialController()

    # 2. [Camera Setup] 配置并打开视频捕获设备
    print(f"[Main] 正在打开摄像头 index={config.CAM_INDEX}...")
    cap = cv2.VideoCapture(config.CAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_HEIGHT)

    # 检查硬件是否就绪
    if not cap.isOpened():
        print("[Error] 无法打开摄像头！请检查 config.py 配置。")
        return

    print("[Main] 系统就绪，按下 'q' 键退出。")

    try:
        while True:
            # 3. [Frame Capture] 读取当前视频帧
            ret, frame = cap.read()
            if not ret:
                print("[Error] 摄像头断开，停止采集")
                break

            # 4. [Visual Processing] 执行人脸检测算法并绘制 UI
            # processed_frame: 带有画框和文字的图片
            # target: (cx, cy) 坐标元组，未检测到为 None
            processed_frame, target = tracker.process_frame(frame)

            # 5. [Serial Communication] 目标坐标解算与发送
            if target:
                # Case A: 检测到目标 -> 发送实时坐标
                comm.send_coordinates(target[0], target[1])
            else:
                # Case B: 目标丢失 -> 保持静默或执行归位逻辑
                # 若需要自动回中，取消下方注释:
                # comm.send_coordinates(320, 240)
                pass

            # 6. [GUI Display] 实时渲染处理后的画面 (HDMI Out)
            cv2.imshow('RK3588 AI Tracker', processed_frame)

            # 7. [Exit Strategy] 检测退出信号
            # 等待 1ms，如果按下 'q' 键则跳出循环
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        # 捕获 Ctrl+C 中断信号
        print("\n[Main] 用户中断 (KeyboardInterrupt)")
    
    finally:
        # [Resource Release] 安全释放硬件资源
        cap.release()
        cv2.destroyAllWindows()
        comm.close()
        print("[Main] 系统资源已释放，程序结束")

if __name__ == "__main__":
    main()