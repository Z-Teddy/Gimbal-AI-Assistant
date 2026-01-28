# Gimbal-AI-Assistant

[![Platform](https://img.shields.io/badge/Platform-RK3588%20%7C%20STM32-blue)](https://www.rockchip.com.cn/)
[![Language](https://img.shields.io/badge/Language-Python%20%7C%20C-green)]()
[![License](https://img.shields.io/badge/License-MIT-orange)](LICENSE)

## 项目简介
**Gimbal-AI-Assistant** 是一款基于异构计算架构的桌面级智能交互终端。项目旨在探索嵌入式边缘计算与运动控制的协同应用，打造一个具备感知、决策与执行能力的桌面机器人。

系统采用 **“上位机决策 + 下位机执行”** 的异构架构：
* **上位机 (Host)**：采用 **RK3588 (Orange Pi 5 Plus)**，利用其突出的 CPU/NPU 算力，负责图像采集、计算机视觉算法处理、多模态大模型推理及高层决策。
* **下位机 (Slave)**：采用 **STM32F103 (野火指南者)**，运行 FreeRTOS 实时操作系统，负责高频 PID 闭环控制、多路舵机 PWM 生成及 OLED/UART 外设逻辑控制。

当前版本 (v1.0) 已实现基于计算机视觉的**人脸锁定与实时跟随**功能。

## 硬件架构

系统硬件分为计算层、控制层与执行层：

| 模块 | 硬件型号/规格 | 功能描述 |
| :--- | :--- | :--- |
| **上位机** | RK3588 (Orange Pi 5 Plus, 8GB) | 运行 Linux 系统，负责图像采集、视觉算法处理、串口通讯 |
| **下位机** | STM32F103VET6 (野火指南者) | 运行 FreeRTOS，负责 PID 运算、PWM 输出、OLED 驱动 |
| **执行器** | SG90 舵机 x 2 | 构成二自由度（Pitch/Yaw）云台结构 |
| **视觉传感器** | 200W 像素 USB 摄像头 | 视频流采集 (640x480 分辨率) |
| **显示模块** | 0.96寸 OLED (SSD1306) | 显示系统状态、IP 地址及追踪坐标数据 |
| **通信链路** | 板载 CH340 (USB-MiniUSB) | 通过开发板集成的 USB 转串口芯片实现 UART 通信 |

## 目录结构

本仓库包含上位机软件与下位机固件两部分：

```text
Gimbal-AI-Assistant/
├── Hardware_STM32/          # 下位机固件源码 (基于 Keil MDK)
│   ├── User/                # 用户应用层代码 (PID算法, 通信协议, 任务调度)
│   ├── FreeRTOS/            # 实时操作系统内核
│   ├── Libraries/           # STM32 标准库与 CMSIS
│   └── Project/             # Keil 工程文件 (.uvprojx)
│
├── Software_RK3588/         # 上位机软件源码 (基于 Python)
│   ├── app/
│   │   ├── models/          # 算法模型文件存放目录
│   │   ├── vision.py        # 视觉处理模块 (OpenCV Haar/RKNN)
│   │   └── serial_ctrl.py   # 串口通信与协议封装
│   ├── config.py            # 系统参数配置文件 (串口号, 摄像头ID, PID参数)
│   ├── main.py              # 程序主入口
│   └── requirements.txt     # Python 依赖库清单
│
└── README.md                # 项目说明文档

```

## 功能特性

### 当前版本 (v1.0)

* **视觉追踪**：基于 OpenCV Haar Cascade 分类器实现人脸检测，模拟人眼注视效果。
* **运动控制**：下位机部署增量式 PID 算法，驱动二自由度云台实现目标跟随。
* **异构通信**：设计了基于帧头/帧尾校验的 UART 通信协议，确保指令传输的完整性。
* **状态监视**：OLED 屏幕实时刷新当前追踪目标的坐标及系统工作模式。

### 开发计划 (Roadmap)

* **v2.0 (NPU 加速)**：迁移视觉算法至 RK3588 NPU，部署 RKNN 量化版 YOLOv8 模型，提升在复杂背景、侧脸及遮挡环境下的识别鲁棒性。
* **v3.0 (语音交互)**：在 RK3588 CPU 端部署离线语音识别（ASR）模型，实现通过语音指令控制云台模式（如追踪/复位/扫描）。
* **v4.0 (多模态集成)**：部署轻量化大语言模型（Qwen），结合语音输入控制 OLED 显示内容（如表情符号），实现多模态交互。

## 快速开始

### 1. 环境准备

* **STM32 开发环境**：Keil uVision 5，需安装 STM32F1 系列 Pack。
* **RK3588 开发环境**：Ubuntu 20.04/22.04 或类似 Linux 发行版，Python 3.8+。

### 2. 硬件连接

1.  **视觉输入**：将 USB 摄像头连接至 Orange Pi 5 的任意 USB 接口。
2.  **通信链路**：使用 **MiniUSB 数据线** 连接 STM32 开发板的 **"USB转串口"** 接口与 Orange Pi 5 的 USB 接口。
    * *注：野火指南者开发板板载 CH340 芯片，内部已连接至 USART1 (PA9/PA10)，无需外部 USB-TTL 模块。*
3.  **执行器 (舵机)**：
    * **X 轴 (Yaw/水平)**：信号线接 **PA2** (TIM2_CH3)，VCC 接 5V。
    * **Y 轴 (Pitch/垂直)**：信号线接 **PA3** (TIM2_CH4)，VCC 接 5V。
    * *⚠️ 注意：舵机建议接 5V 电源以保证驱动力，并确保与开发板共地。*
4.  **显示模块 (OLED)**：
    * **SCL** 接 **PB8**
    * **SDA** 接 **PB9**
    * VCC 接 3.3V

### 3. 部署与运行

**下位机 (STM32):**

1. 进入 `Hardware_STM32/Project` 目录。
2. 使用 Keil 打开工程文件，编译并烧录至 STM32 开发板。
3. 复位开发板，确认 OLED 屏幕正常点亮并显示初始化界面。

**上位机 (RK3588):**

```bash
# 克隆仓库
git clone [https://github.com/Z-Teddy/Gimbal-AI-Assistant.git](https://github.com/Z-Teddy/Gimbal-AI-Assistant.git)

# 进入软件目录
cd Gimbal-AI-Assistant/Software_RK3588

# 安装依赖
pip install -r requirements.txt

# 运行主程序 (建议在连接显示器的桌面环境下运行以查看可视化窗口)
sudo python3 main.py

```

## 许可证

本项目代码遵循 MIT License 开源协议。
