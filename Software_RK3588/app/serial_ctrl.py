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

        # 1. 实例化协议处理类
        self.protocol = GimbalProtocol()
        self.logger = logging.getLogger(__name__)
        self.reconnect_interval_sec = max(
            0.1,
            float(serial_cfg.get("reconnect_interval_sec", 2.0)),
        )
        self.last_send_time = 0
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
        try:
            self.ser.write(packet)
            # 调试打印 (建议在生产环境中注释掉)
            # print(f"[TX] Hex: {packet.hex().upper()}")
        except Exception as exc:
            self.logger.error("串口发送失败: %s", exc)
            self._disconnect("发送失败")

    def close(self):
        """关闭串口资源"""
        if self.ser is not None:
            self.logger.info("关闭串口资源")
            try:
                if self.ser.is_open:
                    self.ser.close()
            finally:
                self.ser = None
