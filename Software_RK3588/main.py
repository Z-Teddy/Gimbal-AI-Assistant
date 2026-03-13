#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : main.py
@Author  : Z-Teddy
@Brief   : 主程序入口 (RK3588 视觉追踪与云台控制)
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import argparse
import logging
import os

import config
from app.logging_setup import setup_logging


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="RK3588 AI Tracker")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--gui", action="store_true", help="以 GUI 模式运行")
    mode_group.add_argument("--headless", action="store_true", help="以无界面模式运行")
    parser.add_argument("--config", default=None, help="指定 YAML 配置文件路径")
    return parser.parse_args()


def resolve_mode_override(args):
    """解析 CLI 模式覆盖参数"""
    if args.gui:
        return "gui"
    if args.headless:
        return "headless"
    return None

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
    args = parse_args()
    config.configure(args.config, mode_override=resolve_mode_override(args))
    log_path = setup_logging(config.get_logging_config())
    logger = logging.getLogger(__name__)

    logger.info("=== RK3588 异构云台追踪系统启动 ===")
    logger.info("配置文件: %s", config.CONFIG_PATH)
    logger.info("运行模式: %s", config.RUNTIME_MODE)
    logger.info("日志文件: %s", log_path)

    if config.RUNTIME_MODE == "gui" and config.RUNTIME_DISPLAY:
        os.environ.setdefault("DISPLAY", config.RUNTIME_DISPLAY)
        logger.info("GUI 显示输出: %s", os.environ.get("DISPLAY"))

    import cv2
    from app.camera_manager import CameraManager
    from app.serial_ctrl import SerialController
    from app.vision import FaceDetector

    # 1. [System Init] 实例化核心功能模块
    tracker = FaceDetector()
    comm = SerialController()
    camera = CameraManager()

    if config.RUNTIME_MODE == "gui":
        logger.info("系统就绪，按下 'q' 键退出。")
    else:
        logger.info("系统就绪，当前为 headless 模式，使用 Ctrl+C 退出。")

    try:
        while True:
            # 3. [Frame Capture] 读取当前视频帧
            frame = camera.read_frame()
            if frame is None:
                comm.try_reconnect()
                if config.RUNTIME_MODE == "gui":
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                continue

            # 4. [Visual Processing] 执行人脸检测算法并绘制 UI
            # processed_frame: 带有画框和文字的图片
            # target: (cx, cy) 坐标元组，未检测到为 None
            processed_frame, target = tracker.process_frame(frame)

            # 5. [Serial Communication] 目标坐标解算与发送
            comm.try_reconnect()
            if target:
                # Case A: 检测到目标 -> 发送实时坐标
                comm.send_coordinates(target[0], target[1])
            else:
                # Case B: 目标丢失 -> 保持静默或执行归位逻辑
                # 若需要自动回中，取消下方注释:
                # comm.send_coordinates(320, 240)
                pass

            # 6. [GUI Display] 实时渲染处理后的画面 (HDMI Out)
            if config.RUNTIME_MODE == "gui":
                cv2.imshow(config.WINDOW_NAME, processed_frame)

                # 7. [Exit Strategy] 检测退出信号
                # 等待 1ms，如果按下 'q' 键则跳出循环
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        # 捕获 Ctrl+C 中断信号
        logger.info("用户中断 (KeyboardInterrupt)")
    
    finally:
        # [Resource Release] 安全释放硬件资源
        camera.close()
        if config.RUNTIME_MODE == "gui":
            cv2.destroyAllWindows()
        comm.close()
        logger.info("系统资源已释放，程序结束")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
