#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : serial_ctrl.py
@Author  : Z-Teddy
@Brief   : 串口通信控制类 (负责硬件连接与数据发送)
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import logging
import time
import serial

import config
from app.protocol import GimbalProtocol

class SerialController:
    """
    串口控制器
    
    管理与下位机 (STM32) 的串口连接，负责发送频率限制、
    坐标系转换以及协议帧的物理发送。
    """

    def __init__(self):
        """
        初始化串口控制器
        
        实例化协议处理对象，并尝试打开串口连接。
        """
        serial_cfg = config.get_settings().get("serial", {})
        protocol_cfg = config.get_settings().get("protocol", {})

        # 1. 实例化协议处理类
        self.protocol = GimbalProtocol()
        self.logger = logging.getLogger(__name__)
        self.reconnect_interval_sec = max(
            0.1,
            float(serial_cfg.get("reconnect_interval_sec", 2.0)),
        )
        self.heartbeat_enabled = bool(protocol_cfg.get("heartbeat_enabled", False))
        self.heartbeat_interval_sec = max(
            0.01,
            float(protocol_cfg.get("heartbeat_interval_sec", 1.0)),
        )
        self.no_target_enabled = bool(protocol_cfg.get("no_target_enabled", False))
        self.no_target_interval_sec = max(
            0.01,
            float(protocol_cfg.get("no_target_interval_sec", 0.2)),
        )
        self.last_send_time = 0
        self.last_heartbeat_time = 0.0
        self.last_no_target_time = 0.0
        self.heartbeat_seq = 0
        self.ser = None
        self.next_reconnect_time = 0.0

        self._connect(initial=True)

    def _connect(self, initial: bool):
        """尝试建立串口连接"""
        if initial:
            action = "正在连接串口"
        else:
            action = "尝试重连串口"

        self.logger.info(
            "%s port=%s baud=%s",
            action,
            config.SERIAL_PORT,
            config.BAUD_RATE,
        )

        try:
            # 根据配置文件初始化串口 (timeout=0.1 防止阻塞)
            self.ser = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=0.1)
            self.next_reconnect_time = 0.0
            if initial:
                self.logger.info("串口首次连接成功: %s", config.SERIAL_PORT)
            else:
                self.logger.info("串口重连成功: %s", config.SERIAL_PORT)
            return True
        except Exception as exc:
            self.ser = None
            self.next_reconnect_time = time.monotonic() + self.reconnect_interval_sec
            if initial:
                self.logger.warning(
                    "串口首次连接失败: %s，将在 %.2f 秒后重试",
                    exc,
                    self.reconnect_interval_sec,
                )
            else:
                self.logger.warning(
                    "串口重连失败: %s，将在 %.2f 秒后继续尝试",
                    exc,
                    self.reconnect_interval_sec,
                )
            return False

    def _disconnect(self, reason: str):
        """关闭当前串口并进入断开状态"""
        if self.ser is not None:
            self.logger.warning("关闭当前串口连接: %s", reason)
            try:
                if self.ser.is_open:
                    self.ser.close()
            except Exception as exc:
                self.logger.warning("关闭串口时出现异常: %s", exc)
            finally:
                self.ser = None

        self.next_reconnect_time = time.monotonic() + self.reconnect_interval_sec

    def try_reconnect(self):
        """未连接时按固定时间间隔尝试重连"""
        if self.ser is not None and self.ser.is_open:
            return

        now = time.monotonic()
        if now < self.next_reconnect_time:
            return

        self._connect(initial=False)

    def _send_packet(self, packet: bytes, failure_reason: str):
        """发送已经封装好的协议包"""
        if self.ser is None or not self.ser.is_open:
            return False

        try:
            self.ser.write(packet)
            return True
        except Exception as exc:
            self.logger.error("串口发送失败: %s", exc)
            self._disconnect(failure_reason)
            return False

    def send_heartbeat(self, status_flags: int = 0, force: bool = False):
        """
        发送心跳包。

        默认受 protocol.heartbeat_enabled 和 heartbeat_interval_sec 控制，
        以保持 v1.5 默认行为兼容。
        """
        if not self.heartbeat_enabled and not force:
            return False

        now = time.monotonic()
        if not force and now - self.last_heartbeat_time < self.heartbeat_interval_sec:
            return False

        packet = self.protocol.pack_heartbeat(self.heartbeat_seq, status_flags)
        if not self._send_packet(packet, "心跳发送失败"):
            return False

        self.last_heartbeat_time = now
        self.heartbeat_seq = (self.heartbeat_seq + 1) & 0xFF
        return True

    def send_no_target(
        self,
        reason_code: int = GimbalProtocol.NO_TARGET_REASON_LOST,
        force: bool = False,
    ):
        """
        发送无目标状态包。

        默认关闭，避免改变 v1.5 在目标丢失时保持静默的行为。
        """
        if not self.no_target_enabled and not force:
            return False

        now = time.monotonic()
        if not force and now - self.last_no_target_time < self.no_target_interval_sec:
            return False

        packet = self.protocol.pack_no_target(reason_code)
        if not self._send_packet(packet, "无目标状态发送失败"):
            return False

        self.last_no_target_time = now
        return True

    def send_coordinates(self, x: int, y: int):
        """
        发送视觉目标坐标 (带频率控制与坐标映射)

        处理流程:
        1. 检查发送频率 (避免串口拥塞)
        2. 坐标映射: 摄像头分辨率 -> STM32 控制分辨率
        3. 边界限幅: 防止坐标越界
        4. 协议打包: 调用 Protocol 生成二进制帧
        5. 物理发送

        Args:
            x (int): 摄像头原始 X 坐标 (0 ~ CAM_WIDTH)
            y (int): 摄像头原始 Y 坐标 (0 ~ CAM_HEIGHT)
        """
        if self.ser is None or not self.ser.is_open:
            return

        # 1. 频率控制 (Frequency Control)
        # 避免发送过快导致下位机处理不过来
        current_time = time.time()
        if current_time - self.last_send_time < config.SEND_INTERVAL:
            return
        self.last_send_time = current_time

        # 2. 坐标空间映射 (Coordinate Mapping)
        # RK3588 负责"看"(高分辨率), STM32 负责"算"(低分辨率 PID)
        # 公式: X_send = X_raw * (Target_W / Source_W)
        map_x = int(x * (config.STM32_WIDTH / config.CAM_WIDTH))
        map_y = int(y * (config.STM32_HEIGHT / config.CAM_HEIGHT))

        # 3. 边界安全限制 (Safety Clamping)
        map_x = max(0, min(config.STM32_WIDTH, map_x))
        map_y = max(0, min(config.STM32_HEIGHT, map_y))

        # 4. 协议封装 (Protocol Packing)
        # 生成格式: AA 55 02 04 [X_Low X_High Y_Low Y_High] [CheckSum]
        packet = self.protocol.pack_face_data(map_x, map_y)

        # 5. 物理发送 (UART Transmit)
        self._send_packet(packet, "发送失败")

    def close(self):
        """关闭串口资源"""
        if self.ser is not None:
            self.logger.info("关闭串口资源")
            try:
                if self.ser.is_open:
                    self.ser.close()
            finally:
                self.ser = None
