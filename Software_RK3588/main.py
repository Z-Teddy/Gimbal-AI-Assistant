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
    protocol_cfg = settings.get("protocol", {})
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
    scan_enabled = bool(control_cfg.get("scan_enabled", False))
    hold_before_scan_sec = max(
        0.0,
        float(control_cfg.get("hold_before_scan_sec", 0.6)),
    )
    scan_timeout_sec = max(
        0.1,
        float(control_cfg.get("scan_timeout_sec", 6.0)),
    )
    return_home_hold_sec = max(
        0.1,
        float(control_cfg.get("return_home_hold_sec", 1.0)),
    )
    scan_period_sec = max(
        0.2,
        float(control_cfg.get("scan_period_sec", 2.4)),
    )
    scan_offset_px = max(
        0,
        int(control_cfg.get("scan_offset_px", max(20, config.CAM_WIDTH // 5))),
    )
    default_mode = str(control_cfg.get("default_mode", "track"))
    current_mode = "hold" if default_mode == "track" else default_mode
    last_target_seen_time = None
    target_detect_streak = 0
    target_miss_streak = 0
    pending_target = None
    mode_entered_at = time.monotonic()
    search_cycle_exhausted = False
    has_ever_seen_target = False
    track_reacquire_grace_sec = max(lost_timeout_sec, 0.6)
    track_grace_until = 0.0

    logger.info("=== RK3588 异构云台追踪系统启动 ===")
    logger.info("配置文件: %s", config.CONFIG_PATH)
    logger.info("运行模式: %s", config.RUNTIME_MODE)
    logger.info("日志文件: %s", log_path)
    detector_cfg = settings.get("detector", {})
    detector_type = str(detector_cfg.get("type", "haar_face"))

    logger.info(
        "控制策略: default_mode=%s startup_mode=%s no_target_mode=%s lost_timeout=%.2fs lost_confirm_frames=%s reacquire_confirm_frames=%s",
        default_mode,
        current_mode,
        no_target_mode,
        lost_timeout_sec,
        lost_confirm_frames,
        reacquire_confirm_frames,
    )
    logger.info(
        "v3控制参数: scan_enabled=%s hold_before_scan=%.2fs scan_timeout=%.2fs return_home_hold=%.2fs scan_period=%.2fs scan_offset_px=%s",
        scan_enabled,
        hold_before_scan_sec,
        scan_timeout_sec,
        return_home_hold_sec,
        scan_period_sec,
        scan_offset_px,
    )
    logger.info("检测器类型: %s", detector_type)
    logger.info(
        "协议开关: heartbeat=%s no_target=%s mode_command=%s",
        bool(protocol_cfg.get("heartbeat_enabled", False)),
        bool(protocol_cfg.get("no_target_enabled", False)),
        bool(protocol_cfg.get("mode_command_enabled", False)),
    )

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
        nonlocal current_mode, mode_entered_at, track_grace_until
        if next_mode == current_mode:
            return False
        logger.info("模式切换: %s -> %s (%s)", current_mode, next_mode, reason)
        current_mode = next_mode
        mode_entered_at = time.monotonic()
        if next_mode == "track":
            track_grace_until = mode_entered_at + track_reacquire_grace_sec
        comm.send_mode(current_mode, force=True)
        return True

    def compute_scan_target(now: float):
        if scan_period_sec <= 0:
            return home_x, home_y

        max_left_span = max(0, home_x)
        max_right_span = max(0, config.CAM_WIDTH - home_x)
        scan_span = max(0, min(scan_offset_px, max_left_span, max_right_span))
        if scan_span == 0:
            return home_x, home_y

        phase = ((now - mode_entered_at) % scan_period_sec) / scan_period_sec
        if phase < 0.5:
            alpha = phase / 0.5
        else:
            alpha = (1.0 - phase) / 0.5

        left_x = home_x - scan_span
        right_x = home_x + scan_span
        scan_x = int(round(left_x + ((right_x - left_x) * alpha)))
        scan_x = max(0, min(config.CAM_WIDTH, scan_x))
        scan_y = max(0, min(config.CAM_HEIGHT, home_y))
        return scan_x, scan_y

    def draw_status_overlay(frame, target_present: bool) -> None:
        if config.RUNTIME_MODE != "gui":
            return

        overlay_lines = (
            f"Mode: {current_mode.upper()}",
            f"Detector: {detector_type}",
            f"Target: {'YES' if target_present else 'NO'}",
        )
        for index, text in enumerate(overlay_lines):
            cv2.putText(
                frame,
                text,
                (20, 70 + (index * 28)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2,
            )

    def handle_no_target_policy(reason: str) -> None:
        nonlocal search_cycle_exhausted
        if no_target_mode == "hold":
            search_cycle_exhausted = True
            mode_changed = update_mode("hold", reason)
            comm.send_no_target(force=mode_changed)
            return

        if no_target_mode == "return_home":
            search_cycle_exhausted = True
            update_mode("return_home", reason)
            return

        if no_target_mode == "scan":
            if not scan_enabled:
                search_cycle_exhausted = True
                mode_changed = update_mode("hold", f"{reason}; scan disabled fallback")
                comm.send_no_target(force=mode_changed)
                return

            search_cycle_exhausted = False
            mode_changed = update_mode("hold", reason)
            comm.send_no_target(force=mode_changed)
            return

        search_cycle_exhausted = True
        update_mode("hold", f"{reason}; fallback unknown no_target_mode={no_target_mode}")
        comm.send_no_target(force=True)

    if config.RUNTIME_MODE == "gui":
        logger.info("系统就绪，按下 'q' 键退出。")
    else:
        logger.info("系统就绪，当前为 headless 模式，使用 Ctrl+C 退出。")

    try:
        while True:
            comm.try_reconnect()
            comm.send_heartbeat()
            comm.send_mode(current_mode)

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
            target_present = target is not None

            # 5. [Serial Communication] 目标坐标解算与发送
            if target_present:
                has_ever_seen_target = True
                target_detect_streak += 1
                target_miss_streak = 0
                pending_target = target

                if current_mode == "track":
                    last_target_seen_time = now
                    search_cycle_exhausted = False
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
                    search_cycle_exhausted = False
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
                        if now >= track_grace_until:
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
                elif current_mode == "hold":
                    if no_target_mode == "hold":
                        comm.send_no_target()
                    elif (
                        no_target_mode == "scan"
                        and scan_enabled
                        and has_ever_seen_target
                        and not search_cycle_exhausted
                        and now - mode_entered_at >= hold_before_scan_sec
                    ):
                        update_mode(
                            "scan",
                            f"hold elapsed {hold_before_scan_sec:.2f}s before scan",
                        )
                elif current_mode == "scan":
                    if now - mode_entered_at >= scan_timeout_sec:
                        search_cycle_exhausted = True
                        update_mode(
                            "return_home",
                            f"scan timeout after {scan_timeout_sec:.2f}s",
                        )
                elif current_mode == "return_home":
                    if now - mode_entered_at >= return_home_hold_sec:
                        search_cycle_exhausted = not (
                            no_target_mode == "scan"
                            and scan_enabled
                            and has_ever_seen_target
                        )
                        update_mode(
                            "hold",
                            f"return_home completed after {return_home_hold_sec:.2f}s",
                        )
                        comm.send_no_target(force=True)
                else:
                    update_mode("hold", f"unexpected mode={current_mode}")
                    comm.send_no_target()

            active_command_target = None
            if current_mode == "track" and pending_target is not None:
                active_command_target = pending_target
            elif current_mode == "scan":
                active_command_target = compute_scan_target(now)

            if active_command_target is not None:
                comm.send_coordinates(active_command_target[0], active_command_target[1])

            draw_status_overlay(processed_frame, target_present)

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
