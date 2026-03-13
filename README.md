# Gimbal-AI-Assistant

[![Platform](https://img.shields.io/badge/Platform-RK3588%20%7C%20STM32-blue)](https://www.rock-chips.com/)
[![Language](https://img.shields.io/badge/Language-Python%20%7C%20C-green)]()
[![License](https://img.shields.io/badge/License-MIT-orange)](LICENSE)

## 项目定位

**长期目标：基于 RK3588 + STM32 异构架构的桌面级嵌入式智能体系统**

**当前阶段：基于 RK3588 + STM32 的异构嵌入式视觉云台系统**

`Gimbal-AI-Assistant` 的长期方向，不是单一的视觉云台功能，而是逐步构建一个具备感知、控制与交互能力的桌面级嵌入式智能体助手。

当前仓库对应的是这个长期目标的第一阶段实现：先围绕“视觉感知 + 云台执行 + Linux 侧工程化”做出一个最小但可运行、可恢复、可部署准备的系统闭环。

## 项目简介

项目采用“RK3588 负责感知与上层运行管理，STM32 负责底层控制与执行”的分工方式：

- RK3588 / OrangePi 负责摄像头采集、OpenCV Haar Cascade 人脸检测、目标中心坐标生成、坐标映射、串口发送，以及 Linux 侧的配置管理、日志、运行模式和异常恢复。
- STM32 负责接收 RK3588 发来的目标坐标，并执行下位机控制与云台驱动相关逻辑。当前仓库中已包含 FreeRTOS / PID / PWM / Servo / 协议相关代码基础。

当前之所以先从视觉云台切入，是因为它同时覆盖了摄像头输入、视觉检测、串口通信、下位机控制、舵机执行与 Linux 侧部署，是整个项目走向更完整桌面助手形态的第一块工程基石。

当前主链路仍保持为：

```text
read -> detect -> send -> display
```

当前版本重点聚焦 RK3588 Linux 侧第一轮工程化能力建设，包括配置管理、日志、双模式运行、设备异常恢复与部署入口准备。

## 当前已实现能力 / 项目亮点

### 系统功能

- 基于 OpenCV Haar Cascade 的人脸检测
- 目标中心坐标生成与视觉坐标到控制坐标的映射
- RK3588 + STM32 异构协同：上位机负责视觉与运行管理，下位机负责底层控制执行
- 串口链路完成目标坐标下发，并与 STM32 下位机控制逻辑打通
- 已形成从视觉输入、目标中心点生成、串口下发到底层执行的最小功能闭环

### RK3588 Linux 侧工程化

- YAML 配置加载：运行参数集中管理在 `Software_RK3588/configs/default.yaml`
- logging：同时输出到控制台与文件 `Software_RK3588/logs/rk3588_tracker.log`
- GUI / headless 双模式：支持本地调试与后台运行
- camera recovery：摄像头连续读帧失败后自动释放并重连
- serial reconnect：串口初始化失败或发送失败后自动重连
- `scripts/run_headless.sh`：headless 启动脚本
- `services/gimbal-ai.service`：systemd service 模板

### 当前已验证情况

- GUI 模式可正常启动
- headless 模式可正常启动
- camera recovery 已做热插拔验证
- serial reconnect 已做断开恢复验证
- `scripts/run_headless.sh` 已手动验证可正常启动
- `gimbal-ai.service` 当前已提供模板文件，但尚未写成自动安装/启用脚本

## 系统硬件组成

| 模块 | 硬件型号 / 规格 | 当前角色 |
| :--- | :--- | :--- |
| 上位机 | RK3588（Orange Pi 5 Plus） | 运行 Linux 侧视觉与工程化逻辑 |
| 下位机 | STM32F103VET6（野火指南者） | 运行底层控制与执行逻辑 |
| 视觉传感器 | USB 摄像头 | 提供图像输入 |
| 执行器 | SG90 舵机 x2 | 构成二自由度云台 |
| 显示模块 | 0.96 寸 OLED（SSD1306） | 用于下位机状态显示 |
| 通信链路 | UART / USB 转串口 | RK3588 与 STM32 间坐标通信 |

## 系统架构说明（简版）

当前系统的基本数据流如下：

1. 摄像头采集图像帧
2. RK3588 执行人脸检测
3. 计算主目标中心坐标
4. 坐标映射到 STM32 控制坐标系
5. 通过串口发送到 STM32
6. STM32 接收后执行底层控制并驱动云台

更完整的说明见：

- [docs/system_architecture.md](docs/system_architecture.md)

## 仓库结构

```text
Gimbal-AI-Assistant/
├── Hardware_STM32/              # STM32 下位机固件工程
│   ├── FreeRTOS/
│   ├── Libraries/
│   ├── Project/
│   └── User/
├── Software_RK3588/             # RK3588 / OrangePi 侧软件
│   ├── app/
│   │   ├── camera_manager.py    # 摄像头管理与自动恢复
│   │   ├── logging_setup.py     # 日志初始化
│   │   ├── protocol.py          # 串口协议打包
│   │   ├── serial_ctrl.py       # 串口发送与自动重连
│   │   ├── settings.py          # YAML 加载与配置校验
│   │   └── vision.py            # 人脸检测与画面标注
│   ├── configs/
│   │   └── default.yaml         # 默认配置文件
│   ├── logs/                    # 运行日志目录
│   ├── scripts/
│   │   └── run_headless.sh      # headless 启动脚本
│   ├── services/
│   │   └── gimbal-ai.service    # systemd service 模板
│   ├── config.py                # 配置兼容层
│   ├── main.py                  # 程序入口
│   └── requirements.txt         # Python 依赖
├── docs/
│   ├── deployment_orangepi.md   # OrangePi / RK3588 部署与运行说明
│   └── system_architecture.md   # 系统架构说明
├── LICENSE
└── README.md
```

## 快速开始

### 1. STM32 侧基本说明

- 使用 Keil 打开 `Hardware_STM32/Project` 下的工程文件
- 编译并烧录到 STM32 开发板
- 确认串口、电源、舵机和 OLED 连接正常

### 2. RK3588 侧环境准备

```bash
cd Software_RK3588
python3 -m pip install -r requirements.txt
```

如使用虚拟环境，请先激活对应环境；在 headless 场景下，也可以直接使用 `scripts/run_headless.sh` 作为统一启动入口。

### 3. 启动方式

#### GUI 模式

适用场景：本地连接显示器，观察 OpenCV 可视化窗口和目标框。

```bash
cd Software_RK3588
python main.py --gui --config configs/default.yaml
```

#### headless 模式

适用场景：无显示器、后台运行或为后续 systemd 托管做验证。

```bash
cd Software_RK3588
python main.py --headless --config configs/default.yaml
```

#### `run_headless.sh` 脚本

适用场景：统一的 headless 启动入口，适合手动执行，也适合被 service 调用。

```bash
bash Software_RK3588/scripts/run_headless.sh
```

### 4. 日志查看

控制台日志会直接输出到终端，同时也会写入文件：

```bash
tail -f Software_RK3588/logs/rk3588_tracker.log
```

## 文档入口

- [系统架构说明](docs/system_architecture.md)
- [OrangePi / RK3588 部署与运行说明](docs/deployment_orangepi.md)

如果后续需要通过 systemd 托管运行，可参考：

- `Software_RK3588/services/gimbal-ai.service`

需要注意，`gimbal-ai.service` 当前只是模板文件，不表示仓库已经提供完整的自动安装、自动启用流程。

## 当前限制

- 摄像头当前依赖固定 `camera.index`
- 串口当前依赖固定 `serial.port`
- 当前视觉算法仍为 OpenCV Haar Cascade
- 更复杂的设备发现机制尚未实现
- 更完整的协议状态机 / 心跳 / safe mode 尚未实现
- `gimbal-ai.service` 当前仍处于模板化准备阶段

## 发展路径

以下内容属于项目的后续方向，不代表当前已经实现：

### 阶段 1：视觉云台最小闭环

当前已完成的重点包括：

- RK3588 + STM32 异构主链路打通
- OpenCV Haar Cascade 人脸检测
- GUI / headless 双模式
- YAML 配置加载
- logging
- camera recovery
- serial reconnect
- `run_headless.sh`
- `gimbal-ai.service` 模板准备

### 阶段 2：更强感知与模型部署

后续可继续推进：

- 更强的人脸检测或目标检测模型
- RKNN / NPU 加速路线评估与落地
- 更稳定的设备发现机制

### 阶段 3：交互与模式扩展

后续可继续推进：

- 更多运行模式与控制模式
- 更完整的协议状态管理与运行监控
- 更完善的部署脚本与 systemd 安装流程

### 阶段 4：向更完整的桌面级智能体形态扩展

更长期的方向包括：

- 在稳定的感知与控制底座上逐步扩展更丰富的交互与任务调度能力
- 从单一视觉云台系统走向更完整的桌面级嵌入式智能体 / 桌面助手形态

## 许可证

本项目遵循 [MIT License](LICENSE)。
