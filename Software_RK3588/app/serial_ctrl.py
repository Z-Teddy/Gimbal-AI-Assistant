#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : serial_ctrl.py
@Author  : Z-Teddy
@Brief   : 串口通信控制类 (负责硬件连接与数据发送)
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

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
        # 1. 实例化协议处理类
        self.protocol = GimbalProtocol()
        
        self.last_send_time = 0
        self.ser = None

        try:
            # 根据配置文件初始化串口 (timeout=0.1 防止阻塞)
            self.ser = serial.Serial(config.SERIAL_PORT, config.BAUD_RATE, timeout=0.1)
            print(f"[Serial] 成功连接至 {config.SERIAL_PORT}")
        except Exception as e:
            print(f"[Serial] 连接失败: {e}")

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
        except Exception as e:
            print(f"[Serial] 发送错误: {e}")

    def close(self):
        """关闭串口资源"""
        if self.ser:
            self.ser.close()