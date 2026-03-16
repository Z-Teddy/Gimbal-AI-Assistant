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
import time

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
    settings = config.get_settings()
    control_cfg = settings.get("control", {})
    log_path = setup_logging(config.get_logging_config())
    logger = logging.getLogger(__name__)

    lost_timeout_sec = max(
        0.0,
        float(control_cfg.get("target_lost_timeout_sec", 0.3)),
    )
    lost_confirm_frames = max(1, int(control_cfg.get("lost_confirm_frames", 2)))
    reacquire_confirm_frames = max(1, int(control_cfg.get("reacquire_confirm_frames", 2)))
    no_target_mode = str(control_cfg.get("no_target_mode", "hold"))
    home_x = int(control_cfg.get("home_x", config.CAM_WIDTH // 2))
    home_y = int(control_cfg.get("home_y", config.CAM_HEIGHT // 2))
    current_mode = str(control_cfg.get("default_mode", "track"))
    last_target_seen_time = None
    return_home_sent = False
    target_detect_streak = 0
    target_miss_streak = 0
    pending_target = None

    logger.info("=== RK3588 异构云台追踪系统启动 ===")
    logger.info("配置文件: %s", config.CONFIG_PATH)
    logger.info("运行模式: %s", config.RUNTIME_MODE)
    logger.info("日志文件: %s", log_path)
    detector_cfg = settings.get("detector", {})
    detector_type = str(detector_cfg.get("type", "haar_face"))

    logger.info(
        "控制策略: default_mode=%s no_target_mode=%s lost_timeout=%.2fs lost_confirm_frames=%s reacquire_confirm_frames=%s",
        current_mode,
        no_target_mode,
        lost_timeout_sec,
        lost_confirm_frames,
        reacquire_confirm_frames,
    )
    logger.info("检测器类型: %s", detector_type)

    if config.RUNTIME_MODE == "gui" and config.RUNTIME_DISPLAY:
        os.environ.setdefault("DISPLAY", config.RUNTIME_DISPLAY)
        logger.info("GUI 显示输出: %s", os.environ.get("DISPLAY"))

    import cv2
    from app.camera_manager import CameraManager
    from app.detectors import create_detector
    from app.serial_ctrl import SerialController

    # 1. [System Init] 实例化核心功能模块
    tracker = create_detector(settings)
    comm = SerialController()
    camera = CameraManager()

    def update_mode(next_mode: str, reason: str) -> bool:
        nonlocal current_mode
        if next_mode == current_mode:
            return False
        logger.info("模式切换: %s -> %s (%s)", current_mode, next_mode, reason)
        current_mode = next_mode
        return True

    def handle_no_target_policy(reason: str) -> None:
        nonlocal return_home_sent
        if no_target_mode == "hold":
            update_mode("hold", reason)
            comm.send_no_target()
            return

        if no_target_mode == "return_home":
            update_mode("return_home", reason)
            if not return_home_sent:
                logger.info(
                    "触发 return_home，发送归位坐标 (%s, %s)",
                    home_x,
                    home_y,
                )
                comm.send_coordinates(home_x, home_y)
                return_home_sent = True
            return

        if no_target_mode == "scan":
            mode_changed = update_mode("scan", reason)
            if mode_changed:
                logger.info("scan 模式当前仅保留占位，未执行扫描动作")
            comm.send_no_target()
            return

        update_mode("hold", f"{reason}; fallback unknown no_target_mode={no_target_mode}")
        comm.send_no_target()

    if config.RUNTIME_MODE == "gui":
        logger.info("系统就绪，按下 'q' 键退出。")
    else:
        logger.info("系统就绪，当前为 headless 模式，使用 Ctrl+C 退出。")

    try:
        while True:
            comm.try_reconnect()
            comm.send_heartbeat()

            # 3. [Frame Capture] 读取当前视频帧
            frame = camera.read_frame()
            if frame is None:
                if config.RUNTIME_MODE == "gui":
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                continue

            # 4. [Visual Processing] 执行人脸检测算法并绘制 UI
            # processed_frame: 带有画框和文字的图片
            # target: (cx, cy) 坐标元组，未检测到为 None
            detection = tracker.process_frame(frame)
            processed_frame = detection.annotated_frame
            target = detection.target_center
            now = time.monotonic()

            # 5. [Serial Communication] 目标坐标解算与发送
            if target:
                target_detect_streak += 1
                target_miss_streak = 0
                pending_target = target

                if current_mode == "track":
                    last_target_seen_time = now
                    return_home_sent = False
                    comm.send_coordinates(target[0], target[1])
                elif target_detect_streak >= reacquire_confirm_frames:
                    if last_target_seen_time is not None:
                        logger.info(
                            "目标重新捕获确认，连续检测 %s 帧，脱靶时长 %.2f 秒",
                            target_detect_streak,
                            max(0.0, now - last_target_seen_time),
                        )
                    else:
                        logger.info(
                            "目标检测确认，连续检测 %s 帧",
                            target_detect_streak,
                        )
                    update_mode(
                        "track",
                        f"target reacquired after {target_detect_streak} consecutive detections",
                    )
                    last_target_seen_time = now
                    return_home_sent = False
                    comm.send_coordinates(pending_target[0], pending_target[1])
            else:
                target_miss_streak += 1
                target_detect_streak = 0
                pending_target = None

                lost_duration = None
                lost_confirmed = False

                if last_target_seen_time is not None:
                    lost_duration = max(0.0, now - last_target_seen_time)
                    lost_confirmed = (
                        target_miss_streak >= lost_confirm_frames
                        and lost_duration >= lost_timeout_sec
                    )
                else:
                    lost_confirmed = target_miss_streak >= lost_confirm_frames

                if current_mode == "track":
                    if lost_confirmed:
                        if lost_duration is not None:
                            lost_reason = (
                                f"target lost confirmed after {target_miss_streak} misses "
                                f"and {lost_duration:.2f}s"
                            )
                        else:
                            lost_reason = (
                                f"target absent at startup after {target_miss_streak} misses"
                            )
                        handle_no_target_policy(lost_reason)
                elif current_mode in {"hold", "return_home", "scan"}:
                    if no_target_mode == "hold":
                        comm.send_no_target()
                else:
                    update_mode("hold", f"unexpected mode={current_mode}")
                    comm.send_no_target()

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
