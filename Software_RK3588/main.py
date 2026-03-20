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
import threading
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
    voice_cfg = settings.get("voice", {})
    voice_override_cfg = voice_cfg.get("override", {})
    log_path = setup_logging(config.get_logging_config())
    logger = logging.getLogger(__name__)

    def enable_voice_debug_logging() -> None:
        voice_logger = logging.getLogger("app.voice")
        voice_logger.setLevel(logging.DEBUG)
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.DEBUG)

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
    voice_enabled = bool(voice_cfg.get("enabled", False))
    voice_device_keyword = str(voice_cfg.get("device_keyword", "USB PnP Sound Device"))
    voice_cooldown_sec = max(0.0, float(voice_cfg.get("cooldown_sec", 1.5)))
    voice_debug = bool(voice_cfg.get("debug", False))
    voice_max_speech_sec = max(0.1, float(voice_cfg.get("max_speech_sec", 8.0)))
    voice_vad_threshold = float(voice_cfg.get("vad_threshold", 0.35))
    voice_min_speech_sec = max(0.0, float(voice_cfg.get("min_speech_sec", 0.3)))
    voice_silence_sec = max(0.0, float(voice_cfg.get("silence_sec", 0.6)))
    voice_input_gain = max(0.1, float(voice_cfg.get("input_gain", 1.0)))
    voice_override_track_sec = max(0.0, float(voice_override_cfg.get("track_sec", 2.5)))
    voice_override_hold_sec = max(0.0, float(voice_override_cfg.get("hold_sec", 10.0)))
    voice_override_scan_sec = max(0.0, float(voice_override_cfg.get("scan_sec", 5.0)))
    voice_override_home_sec = max(0.0, float(voice_override_cfg.get("home_sec", 3.0)))
    voice_log_blocked_transitions = bool(
        voice_override_cfg.get("log_blocked_transitions", True)
    )
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
    logger.info(
        "语音配置: enabled=%s device_keyword=%s cooldown=%.2fs debug=%s",
        voice_enabled,
        voice_device_keyword,
        voice_cooldown_sec,
        voice_debug,
    )
    logger.info(
        "语音采集调优: max_speech=%.2fs vad_threshold=%.2f min_speech=%.2fs silence=%.2fs input_gain=%.1fx",
        voice_max_speech_sec,
        voice_vad_threshold,
        voice_min_speech_sec,
        voice_silence_sec,
        voice_input_gain,
    )
    if voice_enabled and voice_debug:
        enable_voice_debug_logging()
        logger.info("voice.debug=true，已启用 app.voice DEBUG 日志输出。")
    logger.info(
        "语音 override: track=%.1fs hold=%.1fs scan=%.1fs home=%.1fs blocked_log=%s",
        voice_override_track_sec,
        voice_override_hold_sec,
        voice_override_scan_sec,
        voice_override_home_sec,
        voice_log_blocked_transitions,
    )
    if voice_enabled and not bool(protocol_cfg.get("mode_command_enabled", False)):
        logger.warning(
            "voice.enabled=true 但 protocol.mode_command_enabled=false；主程序 mode 会切换，但不会周期下发模式包。"
        )

    if config.RUNTIME_MODE == "gui" and config.RUNTIME_DISPLAY:
        os.environ.setdefault("DISPLAY", config.RUNTIME_DISPLAY)
        logger.info("GUI 显示输出: %s", os.environ.get("DISPLAY"))

    import cv2
    import numpy as np
    from app.camera_manager import CameraManager
    from app.detectors import create_detector
    from app.serial_ctrl import SerialController
    from app.voice.override_state import VoiceOverrideController

    # 1. [System Init] 实例化核心功能模块
    tracker = create_detector(settings)
    comm = SerialController()
    camera = CameraManager()
    camera_enabled = True
    last_voice_command = "IDLE"
    last_voice_text = ""
    voice_listener = None
    voice_thread = None
    voice_bridge = None
    voice_runtime_context = None
    voice_override = VoiceOverrideController() if voice_enabled else None
    voice_mode_override_map = {}

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

    def expire_voice_override_if_needed(now: float = None) -> None:
        if voice_override is None:
            return

        now = time.monotonic() if now is None else now
        expired_snapshot = voice_override.expire_if_needed(now)
        if expired_snapshot.active:
            logger.info("voice override expired: mode=%s", expired_snapshot.mode.upper())

    def set_voice_override(mode: str, *, text: str = "", source: str = "voice") -> None:
        if voice_override is None:
            return

        # HOLD 这里采用“较长固定窗口”而不是“直到下一条语音命令”，
        # 这样能避免检测抖动时立刻被自动状态机抢回，同时也不会形成永久锁定。
        duration_map = {
            "track": voice_override_track_sec,
            "hold": voice_override_hold_sec,
            "scan": voice_override_scan_sec,
            "return_home": voice_override_home_sec,
        }
        duration_sec = duration_map.get(mode, 0.0)
        now = time.monotonic()
        previous_snapshot = voice_override.snapshot()
        if previous_snapshot.active and previous_snapshot.until > now:
            if previous_snapshot.mode != mode:
                logger.info(
                    "voice override cleared by command: previous_mode=%s new_mode=%s",
                    previous_snapshot.mode.upper(),
                    mode.upper(),
                )
            else:
                logger.info("voice override refreshed by command: mode=%s", mode.upper())

        voice_override.set(mode, duration_sec, source=source, text=text, now=now)
        if duration_sec > 0.0:
            logger.info(
                "voice override set: mode=%s source=%s text=%s duration=%.1fs",
                mode.upper(),
                source,
                text or "-",
                duration_sec,
            )
        else:
            logger.info(
                "voice override skipped: mode=%s source=%s text=%s duration=%.1fs",
                mode.upper(),
                source,
                text or "-",
                duration_sec,
            )

    def request_auto_mode_update(next_mode: str, reason: str, *, now: float = None) -> str:
        if voice_override is None:
            return "changed" if update_mode(next_mode, reason) else "unchanged"

        now = time.monotonic() if now is None else now
        expire_voice_override_if_needed(now)
        if voice_override.should_block(next_mode, now):
            if (
                voice_log_blocked_transitions
                and voice_override.should_log_blocked(next_mode, now=now)
            ):
                logger.info(
                    "auto transition blocked by voice override: requested=%s override=%s remaining=%.1fs",
                    next_mode,
                    voice_override.current_mode(now).upper(),
                    voice_override.remaining_sec(now),
                )
            return "blocked"

        return "changed" if update_mode(next_mode, reason) else "unchanged"

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

        overlay_lines = [
            f"Mode: {current_mode.upper()}",
            f"Detector: {detector_type}",
            f"Target: {'YES' if target_present else 'NO'}",
        ]
        if voice_enabled:
            overlay_lines.append(f"Voice: {last_voice_command}")
        overlay_lines.append(f"Camera: {'ON' if camera_enabled else 'OFF'}")
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
            mode_state = request_auto_mode_update("hold", reason)
            if mode_state == "blocked":
                return
            comm.send_no_target(force=mode_state == "changed")
            return

        if no_target_mode == "return_home":
            search_cycle_exhausted = True
            request_auto_mode_update("return_home", reason)
            return

        if no_target_mode == "scan":
            if not scan_enabled:
                search_cycle_exhausted = True
                mode_state = request_auto_mode_update(
                    "hold",
                    f"{reason}; scan disabled fallback",
                )
                if mode_state == "blocked":
                    return
                comm.send_no_target(force=mode_state == "changed")
                return

            search_cycle_exhausted = False
            mode_state = request_auto_mode_update("hold", reason)
            if mode_state == "blocked":
                return
            comm.send_no_target(force=mode_state == "changed")
            return

        search_cycle_exhausted = True
        mode_state = request_auto_mode_update(
            "hold",
            f"{reason}; fallback unknown no_target_mode={no_target_mode}",
        )
        if mode_state == "blocked":
            return
        comm.send_no_target(force=mode_state == "changed")

    def set_last_voice_status(command_label: str, text: str = "") -> None:
        nonlocal last_voice_command, last_voice_text
        last_voice_command = command_label
        last_voice_text = text

    def set_camera_enabled(next_enabled: bool, reason: str) -> bool:
        nonlocal camera_enabled, pending_target, target_detect_streak, target_miss_streak, last_target_seen_time
        if next_enabled == camera_enabled:
            return False

        camera_enabled = next_enabled
        pending_target = None
        target_detect_streak = 0
        target_miss_streak = 0
        last_target_seen_time = None

        if next_enabled:
            camera.read_failures = 0
            camera.next_reconnect_time = 0.0
            logger.info("摄像头状态切换: OFF -> ON (%s)", reason)
        else:
            camera.close()
            logger.info("摄像头状态切换: ON -> OFF (%s)", reason)

        return True

    if voice_enabled:
        from app.voice.config import VoiceRuntimeConfig
        from app.voice.command_parser import VoiceCommand
        from app.voice.realtime_listener import VoiceRealtimeListener
        from app.voice.runtime_bridge import (
            VoiceCommandBridge,
            VoiceRuntimeContext,
            apply_voice_command_to_runtime,
        )

        voice_mode_override_map = {
            VoiceCommand.TRACK: "track",
            VoiceCommand.HOLD: "hold",
            VoiceCommand.SCAN: "scan",
            VoiceCommand.HOME: "return_home",
        }
        voice_bridge = VoiceCommandBridge()
        voice_runtime_context = VoiceRuntimeContext(
            update_mode=update_mode,
            set_camera_enabled=set_camera_enabled,
            set_last_voice_status=set_last_voice_status,
            logger=logger,
        )

        def on_voice_result(result) -> None:
            set_last_voice_status(result.command.value, result.text)
            queued = voice_bridge.enqueue_result(result)
            queue_reason = "queued"
            if result.suppressed:
                queue_reason = "suppressed_by_cooldown"
            elif result.raw_action == "noop":
                queue_reason = "unknown_command"
            elif not queued:
                queue_reason = "filtered"

            log_message = (
                "语音结果: ASR=%s CMD=%s ACTION=%s queued=%s reason=%s duration=%.2fs"
            )
            if queued:
                logger.info(
                    log_message,
                    result.text,
                    result.command.value,
                    result.action,
                    queued,
                    queue_reason,
                    result.speech_duration_sec,
                )
            else:
                logger.warning(
                    log_message,
                    result.text,
                    result.command.value,
                    result.action,
                    queued,
                    queue_reason,
                    result.speech_duration_sec,
                )
            if voice_debug and result.segment_path:
                logger.info("语音调试语音段: %s", result.segment_path)

        voice_listener = VoiceRealtimeListener(
            runtime_config=VoiceRuntimeConfig(
                record_device_keyword=voice_device_keyword,
                cooldown_sec=voice_cooldown_sec,
                max_speech_sec=voice_max_speech_sec,
                vad_threshold=voice_vad_threshold,
                min_speech_sec=voice_min_speech_sec,
                silence_sec=voice_silence_sec,
                input_gain=voice_input_gain,
            ),
            debug=voice_debug,
        )
        voice_thread = threading.Thread(
            target=voice_listener.run_forever,
            kwargs={"on_result": on_voice_result},
            name="voice-listener",
            daemon=True,
        )
        voice_thread.start()
        logger.info("语音监听线程已启动")

    if config.RUNTIME_MODE == "gui":
        logger.info("系统就绪，按下 'q' 键退出。")
    else:
        logger.info("系统就绪，当前为 headless 模式，使用 Ctrl+C 退出。")

    try:
        while True:
            comm.try_reconnect()
            comm.send_heartbeat()
            comm.send_mode(current_mode)

            if voice_bridge is not None and voice_runtime_context is not None:
                for voice_event in voice_bridge.poll_voice_commands():
                    override_mode = voice_mode_override_map.get(voice_event.command)
                    if override_mode:
                        set_voice_override(
                            override_mode,
                            text=voice_event.text,
                            source="voice",
                        )
                    bridge_result = apply_voice_command_to_runtime(
                        voice_event,
                        voice_runtime_context,
                    )
                    if bridge_result.success:
                        logger.info(
                            "主线程已应用语音命令: cmd=%s text=%s detail=%s",
                            voice_event.command.value,
                            voice_event.text,
                            bridge_result.detail,
                        )
                    else:
                        logger.warning(
                            "主线程应用语音命令失败: cmd=%s text=%s detail=%s",
                            voice_event.command.value,
                            voice_event.text,
                            bridge_result.detail,
                        )

            if not camera_enabled:
                if config.RUNTIME_MODE == "gui":
                    blank_frame = np.zeros((config.CAM_HEIGHT, config.CAM_WIDTH, 3), dtype=np.uint8)
                    draw_status_overlay(blank_frame, False)
                    if last_voice_text:
                        cv2.putText(
                            blank_frame,
                            f"Voice Text: {last_voice_text[:40]}",
                            (20, 70 + (4 * 28)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            (0, 200, 255),
                            2,
                        )
                    cv2.imshow(config.WINDOW_NAME, blank_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                else:
                    time.sleep(0.05)
                continue

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
                    if target_detect_streak == reacquire_confirm_frames:
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
                    if (
                        request_auto_mode_update(
                            "track",
                            f"target reacquired after {target_detect_streak} consecutive detections",
                            now=now,
                        )
                        != "blocked"
                    ):
                        last_target_seen_time = now
                        search_cycle_exhausted = False
                    else:
                        last_target_seen_time = now
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
                        request_auto_mode_update(
                            "scan",
                            f"hold elapsed {hold_before_scan_sec:.2f}s before scan",
                            now=now,
                        )
                elif current_mode == "scan":
                    if now - mode_entered_at >= scan_timeout_sec:
                        search_cycle_exhausted = True
                        request_auto_mode_update(
                            "return_home",
                            f"scan timeout after {scan_timeout_sec:.2f}s",
                            now=now,
                        )
                elif current_mode == "return_home":
                    if now - mode_entered_at >= return_home_hold_sec:
                        search_cycle_exhausted = not (
                            no_target_mode == "scan"
                            and scan_enabled
                            and has_ever_seen_target
                        )
                        mode_state = request_auto_mode_update(
                            "hold",
                            f"return_home completed after {return_home_hold_sec:.2f}s",
                            now=now,
                        )
                        if mode_state != "blocked":
                            comm.send_no_target(force=True)
                else:
                    mode_state = request_auto_mode_update(
                        "hold",
                        f"unexpected mode={current_mode}",
                        now=now,
                    )
                    if mode_state != "blocked":
                        comm.send_no_target()

            active_command_target = None
            if current_mode == "track" and pending_target is not None:
                active_command_target = pending_target
            elif current_mode == "scan":
                active_command_target = compute_scan_target(now)

            if active_command_target is not None:
                comm.send_coordinates(active_command_target[0], active_command_target[1])

            draw_status_overlay(processed_frame, target_present)
            if config.RUNTIME_MODE == "gui" and voice_enabled and last_voice_text:
                cv2.putText(
                    processed_frame,
                    f"Voice Text: {last_voice_text[:40]}",
                    (20, 70 + (4 * 28)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 200, 255),
                    2,
                )

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
        if voice_listener is not None:
            voice_listener.stop()
        if voice_thread is not None:
            voice_thread.join(timeout=2.0)
            if voice_thread.is_alive():
                logger.warning("语音监听线程未在超时时间内退出")
            else:
                logger.info("语音监听线程已退出")
        camera.close()
        if config.RUNTIME_MODE == "gui":
            cv2.destroyAllWindows()
        comm.close()
        logger.info("系统资源已释放，程序结束")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
