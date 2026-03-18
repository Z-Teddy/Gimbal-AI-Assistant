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

- RK3588 / OrangePi 负责摄像头采集、目标检测、主目标中心坐标生成、坐标映射、串口发送，以及 Linux 侧的配置管理、日志、运行模式和异常恢复。当前已支持 `haar_face` 与 `retinaface` 两种 detector 后端，其中 `retinaface` 基于 RK3588 NPU / RKNNLite 部署。
- STM32 负责接收 RK3588 发来的目标坐标，并执行下位机控制与云台驱动相关逻辑。当前仓库中已包含 FreeRTOS / PID / PWM / Servo / 协议相关代码基础。

当前之所以先从视觉云台切入，是因为它同时覆盖了摄像头输入、视觉检测、串口通信、下位机控制、舵机执行与 Linux 侧部署，是整个项目走向更完整桌面助手形态的第一块工程基石。

当前主链路仍保持为：

```text
read -> detect -> send -> display
```

当前公开代码已经从 v1.5 的 RK3588 Linux 工程化基线，推进到 **v2.5：在 v2.0 第一轮状态化与 detector 模块化基础上，补齐 RetinaFace / RKNNLite 第二个 detector 并完成主程序联调收口**。

## v2.5 新增能力

在 v2.0 第一轮基础上，当前仓库已完成一轮面向 `retinaface` 的增量收口：

- 新增第二个 detector：`retinaface`，可与 `haar_face` 按 `detector.type` 切换
- `retinaface` 基于 RK3588 NPU / RKNNLite 部署
- 已完成官方 RetinaFace `.onnx -> .rknn` 模型转换链，当前板端加载 `.rknn` 推理
- 已完成单图 smoke test，以及 GUI / headless 两种主程序模式联调
- `track / hold` 状态机与现有串口链路在 RetinaFace 路径下保持兼容

## 当前已实现能力 / 项目亮点

### 系统功能

- 支持 `haar_face` / `retinaface` 双 detector 人脸检测，其中 `retinaface` 基于 RK3588 NPU / RKNNLite
- detector 模块化第一轮完成，已落地两个真实实现，可通过 `detector.type` 切换
- 目标中心坐标生成与视觉坐标到控制坐标的映射
- RK3588 + STM32 异构协同：上位机负责视觉与运行管理，下位机负责底层控制执行
- 最小模式状态机：`track / hold / return_home`（`scan` 当前仅保留占位）
- 主循环去抖 / 滞回优化，降低瞬时漏检导致的 `track <-> hold` 抖动
- 串口链路完成目标坐标、heartbeat、no-target 的最小状态化发送，并与 STM32 下位机控制逻辑打通
- 已形成从视觉输入、目标中心点生成、串口下发到底层执行的最小功能闭环

### RK3588 Linux 侧工程化

- YAML 配置加载：运行参数集中管理在 `Software_RK3588/configs/default.yaml`
- logging：同时输出到控制台与文件 `Software_RK3588/logs/rk3588_tracker.log`
- GUI / headless 双模式：支持本地调试与后台运行
- camera recovery：摄像头连续读帧失败后自动释放并重连
- serial reconnect：串口初始化失败或发送失败后自动重连
- `scripts/run_headless.sh`：headless 启动脚本
- `scripts/install_service.sh` / `scripts/uninstall_service.sh`：systemd 服务安装与卸载
- `scripts/find_devices.sh`：设备发现与配置提示脚本
- `services/gimbal-ai.service`：systemd service 模板
- `docs/communication_protocol.md`：当前真实协议文档

### 当前已验证情况

- GUI 模式可正常启动
- headless 模式可正常启动
- camera recovery 已做热插拔验证
- serial reconnect 已做断开恢复验证
- `scripts/run_headless.sh` 已手动验证可正常启动
- detector 模块化第一轮已做回归，`haar_face` 路径行为保持稳定
- RetinaFace RKNNLite 板端单图 smoke test 已通过，可验证模型加载、推理输出、后处理与 `target_center`
- RetinaFace 已完成 GUI / headless 主程序联调，可正常检测与跟踪人脸
- RetinaFace 路径下 `track / hold` 状态机与现有串口链路保持正常
- 主循环去抖 / 滞回优化已做实测，`track <-> hold` 高频抖动明显降低
- heartbeat / no-target / link-timeout safe hold 的最小双端状态闭环已验证通过
- 串口中途断开后，serial reconnect 与 camera recovery 链路保持可用

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
2. RK3588 执行 detector 推理（当前支持 `haar_face` / `retinaface`）
3. 计算主目标中心坐标
4. 坐标映射到 STM32 控制坐标系
5. 通过串口发送到 STM32
6. STM32 接收后执行底层控制并驱动云台

更完整的说明见：

- [docs/system_architecture.md](docs/system_architecture.md)

## 仓库结构

```text
Gimbal-AI-Assistant/
├── Hardware_STM32/              # STM32 下位机固件工程（Keil + FreeRTOS）
│   ├── FreeRTOS/                # FreeRTOS 内核源码与移植层（工程使用 Cortex-M3）
│   │   ├── include/
│   │   ├── port/
│   │   └── src/
│   ├── Libraries/               # STM32F10x CMSIS / 标准外设库
│   │   ├── CMSIS/
│   │   └── FWlib/
│   ├── Project/
│   │   └── RVMDK（uv5）/        # Keil uVision5 工程入口（STM32F103VE）
│   └── User/                    # 下位机应用层与板级驱动
│       ├── APP/                 # 协议解析、PID 控制、PWM/Servo、OLED 等核心模块
│       │   ├── protocol.c       # 串口协议解析、状态机、命令分发、link alive / no-target 处理
│       │   ├── PID.c            # 云台 PID 控制
│       │   ├── PWM.c            # PWM 输出
│       │   ├── Servo.c          # 舵机控制
│       │   └── OLED.c           # OLED 显示
│       ├── uart/                # 串口 BSP 与上位机通信接收
│       ├── led/                 # LED 板级驱动
│       ├── key/                 # 按键板级驱动
│       ├── FreeRTOSConfig.h     # RTOS 配置
│       ├── freertos_hooks.c     # 栈溢出 / 内存失败钩子
│       └── main.c               # 控制任务、GUI 任务与系统入口
├── Software_RK3588/             # RK3588 / OrangePi 侧软件
│   ├── app/
│   │   ├── camera_manager.py    # 摄像头管理与自动恢复
│   │   ├── detectors/           # detector 模块化目录
│   │   │   ├── base.py
│   │   │   ├── haar_detector.py
│   │   │   ├── retinaface_postprocess.py
│   │   │   └── rknn_retinaface.py
│   │   ├── logging_setup.py     # 日志初始化
│   │   ├── protocol.py          # 串口协议打包
│   │   ├── serial_ctrl.py       # 串口发送与自动重连
│   │   ├── settings.py          # YAML 加载与配置校验
│   │   └── vision.py            # 视觉兼容包装层
│   ├── configs/
│   │   └── default.yaml         # 默认配置文件
│   ├── logs/                    # 运行日志目录
│   ├── models/
│   │   └── retinaface/          # RetinaFace RKNN 模型目录
│   ├── scripts/
│   │   ├── find_devices.sh      # 设备发现脚本
│   │   ├── install_service.sh   # service 安装脚本
│   │   ├── run_headless.sh      # headless 启动脚本
│   │   ├── test_retinaface_rknn.py # RetinaFace 单图 smoke test
│   │   └── uninstall_service.sh # service 卸载脚本
│   ├── services/
│   │   └── gimbal-ai.service    # systemd service 模板
│   ├── config.py                # 配置兼容层
│   ├── main.py                  # 程序入口
│   └── requirements.txt         # Python 依赖
├── docs/
│   ├── communication_protocol.md # 通信协议说明
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

### 3. 设备确认与配置

在修改 `configs/default.yaml` 之前，建议先查看当前系统枚举到的摄像头和串口：

```bash
bash Software_RK3588/scripts/find_devices.sh
```

当前建议：

- `camera.index` 仍填写数值索引
- `serial.port` 优先填写 `/dev/serial/by-id/*`
- 当前支持 `detector.type = "haar_face"` 与 `detector.type = "retinaface"`；未准备 `.rknn` 模型文件时可先使用 `haar_face`

### RetinaFace 模型说明

- 当前使用模型：`RetinaFace_mobile320.rknn`
- 建议放置路径：`Software_RK3588/models/retinaface/RetinaFace_mobile320.rknn`
- 板端只负责加载 `.rknn` 推理，`.onnx -> .rknn` 转换在板外完成
- 模型来源：官方 `rknn_model_zoo` 的 RetinaFace 示例，原始 ONNX 模型为 `RetinaFace_mobile320.onnx`
- 参考获取与转换方式：
  - 下载 ONNX：`examples/RetinaFace/model/download_model.sh`
  - 转换命令：`python convert.py ../model/RetinaFace_mobile320.onnx rk3588`
- 官方 RetinaFace 示例与转换说明见：
  - `https://github.com/airockchip/rknn_model_zoo/tree/main/examples/RetinaFace`

### RetinaFace 单图 smoke test

`Software_RK3588/scripts/test_retinaface_rknn.py` 用于单图 smoke test，可快速验证模型加载、推理输出、后处理以及 `target_center` 是否正常。

最小命令示例：

```bash
cd Software_RK3588
python scripts/test_retinaface_rknn.py --image /path/to/test.jpg
```

### 4. 启动方式

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

#### 安装 systemd 服务

适用场景：OrangePi / RK3588 长期后台运行。

```bash
bash Software_RK3588/scripts/install_service.sh
```

卸载：

```bash
bash Software_RK3588/scripts/uninstall_service.sh
```

### 5. 日志查看

控制台日志会直接输出到终端，同时也会写入文件：

```bash
tail -f Software_RK3588/logs/rk3588_tracker.log
```

## 文档入口

- [系统架构说明](docs/system_architecture.md)
- [OrangePi / RK3588 部署与运行说明](docs/deployment_orangepi.md)
- [RK3588 <-> STM32 通信协议说明](docs/communication_protocol.md)

## 当前限制

- 摄像头当前依赖固定 `camera.index`
- 串口配置当前仍依赖固定 `serial.port`，虽然现在已提供设备发现脚本
- 当前已支持 `haar_face` 与 `retinaface` 两种 detector；其中 `retinaface` 第一版固定为 `input_size = 320`
- RetinaFace 的 landmark 当前仅作为检测附带输出 / 可选绘制，不进入控制链
- `scan` 当前仅保留配置和日志占位，没有真实扫描动作
- `CMD_SET_MODE` 当前仅是预留协议入口，还没有完整上下位机模式闭环
- 当前协议仍是单向主链路，没有下位机状态回传、ACK 或重传机制

## 发展路径

以下内容属于项目的后续方向，不代表当前已经实现：

### 阶段 1：视觉云台最小闭环

当前已完成的重点包括：

- RK3588 + STM32 异构主链路打通
- 双 detector 人脸检测：OpenCV Haar Cascade / RetinaFace RKNNLite
- GUI / headless 双模式
- YAML 配置加载
- logging
- camera recovery
- serial reconnect
- `run_headless.sh`
- `gimbal-ai.service` 模板准备

### 阶段 2：v2.0 第一轮状态化与可部署性收口

当前已完成的重点包括：

- detector 模块化第一轮
- 最小模式状态机与去抖 / 滞回
- heartbeat / no-target / link-timeout safe hold
- 最小双端状态闭环
- service 安装/卸载脚本
- 设备发现脚本与协议文档

### 阶段 3：更强感知与模式扩展

后续可继续推进：

- 更完整的 mode command 闭环
- `scan` 动作与更明确的 return-home 策略
- 更细的状态回传 / ACK / 协议增强
- RetinaFace 后端进一步稳定性与部署收口

### 阶段 4：向更完整的桌面级智能体形态扩展

更长期的方向包括：

- 在稳定的感知与控制底座上逐步扩展更丰富的交互与任务调度能力
- 从单一视觉云台系统走向更完整的桌面级嵌入式智能体 / 桌面助手形态

## 许可证

本项目遵循 [MIT License](LICENSE)。
