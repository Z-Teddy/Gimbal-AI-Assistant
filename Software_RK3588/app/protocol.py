#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File    : protocol.py
@Author  : Z-Teddy
@Brief   : 通信协议封装类 (RK3588 -> STM32)
@Repo    : https://github.com/Z-Teddy/Gimbal-AI-Assistant
"""

import struct

class GimbalProtocol:
    """
    云台通信协议处理类
    
    负责将控制指令打包为符合下位机解析规则的二进制帧。
    帧结构: [Head1][Head2][CMD][Len][Payload][Checksum]
    """

    # ==========================================================================
    # 协议常量定义
    # ==========================================================================
    HEAD1 = 0xAA
    HEAD2 = 0x55

    # --- 功能字 (Command ID) ---
    CMD_HEARTBEAT      = 0x01  # 心跳包 
    CMD_TRACK_FACE     = 0x02  # 视觉追踪: [x(int16), y(int16)]
    CMD_SET_ANGLE      = 0x03  # 语音强控: [yaw(float), pitch(float)]
    CMD_SET_EXPRESSION = 0x04  # 表情切换: [face_id(uint8)]

    def _pack(self, cmd_id, payload=b''):
        """
        [内部方法] 构建通用通信帧

        帧结构说明:
        - Head: 0xAA 0x55
        - CMD:  功能字
        - Len:  Payload 长度
        - Load: 数据载荷
        - Sum:  校验和 (CMD + Len + sum(Payload)) & 0xFF

        Args:
            cmd_id (int): 功能指令 ID
            payload (bytes, optional): 数据载荷. Defaults to b''.

        Returns:
            bytes: 完整的二进制协议帧
        """
        data_len = len(payload)
        
        # 校验和计算: CMD + LEN + 所有载荷字节之和 (仅取低8位)
        checksum = (cmd_id + data_len + sum(payload)) & 0xFF

        # 格式: Head1(B), Head2(B), CMD(B), Len(B)
        header = struct.pack('BBBB', self.HEAD1, self.HEAD2, cmd_id, data_len)
        
        # 尾部校验和
        tail = struct.pack('B', checksum)
        
        return header + payload + tail

    def pack_face_data(self, x, y):
        """
        打包视觉追踪坐标数据 (CMD: 0x02)

        用于将视觉算法识别到的人脸中心坐标发送给下位机 PID 控制器。

        Args:
            x (int): 目标的 X 轴坐标 (int16, 范围 -32768 ~ 32767)
            y (int): 目标的 Y 轴坐标 (int16, 范围 -32768 ~ 32767)

        Returns:
            bytes: 打包后的协议帧
        """
        # '<hh': 小端模式 (Little Endian), 两个 short (int16)
        # 强制转换为 int 以防止传入 float 导致 struct 报错
        payload = struct.pack('<hh', int(x), int(y))
        return self._pack(self.CMD_TRACK_FACE, payload)

    def pack_angle_control(self, yaw, pitch):
        """
        打包绝对角度控制指令 (CMD: 0x03)

        用于语音指令强控，直接指定云台的目标角度。

        Args:
            yaw (float): 偏航角 (float, 小端)
            pitch (float): 俯仰角 (float, 小端)

        Returns:
            bytes: 打包后的协议帧
        """
        # '<ff': 小端模式, 两个 float (32-bit IEEE 754)
        payload = struct.pack('<ff', float(yaw), float(pitch))
        return self._pack(self.CMD_SET_ANGLE, payload)

    def pack_expression(self, face_id):
        """
        打包表情切换指令 (CMD: 0x04)

        Args:
            face_id (int): 表情 ID 索引 (uint8, 0~255)

        Returns:
            bytes: 打包后的协议帧
        """
        # 'B': unsigned char (uint8)
        payload = struct.pack('B', int(face_id))
        return self._pack(self.CMD_SET_EXPRESSION, payload)