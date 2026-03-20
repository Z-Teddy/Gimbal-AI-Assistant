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

当前公开代码已经从 v1.5 的 RK3588 Linux 工程化基线，推进到 **v4.0：在 v3.0 模式闭环与主动搜索链路基础上，补齐本地实时语音命令输入并接入主程序运行时**。

## v4.0 新增能力

在 v3.0 第一轮模式闭环基础上，当前仓库补齐了面向 GUI / headless 联调与演示的本地实时语音能力：

- 新增 `app/voice/` 模块，包含 SenseVoice ASR、Silero VAD、命令词解析与主程序桥接
- 新增实时语音线程，并通过线程安全队列把语音命令交回主线程消费
- 语音命令可直接驱动现有 `TRACK / HOLD / SCAN / RETURN_HOME` 模式主链路
- 新增 `OPEN_CAMERA / CLOSE_CAMERA` 语义，并接入主线程 camera runtime
- 新增 `voice override` 机制，避免语音 mode 被自动状态机立即抢回
- 新增 `tools/voice_realtime_test.py` 与 `scripts/run_voice.sh`
- 提供“基础配置 + 场景配置”结构，避免继续按版本号维护 YAML

## 当前支持的语音命令

- `开始跟踪 / 跟踪 / 跟踪目标 / 追踪` -> `TRACK`
- `停止 / 停止跟踪 / 停止追踪 / 保持 / 待机` -> `HOLD`
- `开始扫描 / 扫描 / 搜索目标 / 搜索` -> `SCAN`
- `回中 / 回到中位 / 归位 / 回家` -> `HOME`
- `打开摄像头 / 开启摄像头` -> `OPEN_CAMERA`
- `关闭摄像头 / 关掉摄像头` -> `CLOSE_CAMERA`

## v4.0 能力边界

- 当前语音能力是“本地命令词输入”，不是自由对话助手
- 当前未引入唤醒词
- 当前不依赖 LLM
- 当前优先使用 USB 麦克风演示，板载 MIC 噪声较大
- 当前语音命令主要面向中文短句控制场景

## 当前已实现能力 / 项目亮点

### 系统功能

- 支持 `haar_face` / `retinaface` 双 detector 人脸检测，其中 `retinaface` 基于 RK3588 NPU / RKNNLite
- detector 模块化第一轮完成，已落地两个真实实现，可通过 `detector.type` 切换
- 目标中心坐标生成与视觉坐标到控制坐标的映射
- RK3588 + STM32 异构协同：上位机负责视觉与运行管理，下位机负责底层控制执行
- 最小模式状态机：`track / hold / scan / return_home`
- 主循环去抖 / 滞回优化，降低瞬时漏检导致的 `track <-> hold` 抖动
- RK3588 侧实现 scan 轨迹生成；STM32 在 `return_home` 模式下执行物理回中
- 串口链路完成目标坐标、heartbeat、no-target、mode command 的最小状态化发送，并与 STM32 下位机控制逻辑打通
- 本地实时语音输入：USB 麦克风常驻监听、Silero VAD、SenseVoice 离线识别、命令词解析
- 语音命令可作为主程序的额外输入模态接入 GUI / headless 运行时
- `voice override` 机制可在短时间窗口内保护语音 mode 命令，避免自动状态机立即覆盖
- 已形成从视觉输入、目标中心点生成、串口下发到底层执行的最小功能闭环

### RK3588 Linux 侧工程化

- YAML 配置加载：运行参数集中管理在 `Software_RK3588/configs/default.yaml`
- logging：同时输出到控制台与文件 `Software_RK3588/logs/rk3588_tracker.log`
- GUI / headless 双模式：支持本地调试与后台运行
- camera recovery：摄像头连续读帧失败后自动释放并重连
- serial reconnect：串口初始化失败或发送失败后自动重连
- `scripts/run_headless.sh`：headless 启动脚本
- `scripts/run_voice.sh`：语音 + 主程序一体化启动脚本（默认 GUI，可透传 `--headless`）
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
- RetinaFace 路径下 `track / hold / scan / return_home` 状态机代码路径与现有串口链路保持兼容
- 实时语音监听、命令解析、主线程桥接、override 与退出流程已完成板端联调
- 主循环去抖 / 滞回优化已做实测，`track <-> hold` 高频抖动明显降低
- heartbeat / no-target / mode command / link-timeout safe hold 的最小双端状态闭环已打通
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
4. 语音线程可并行执行 `USB 麦克风 -> VAD -> ASR -> VoiceCommand`
5. 主线程统一消费视觉状态与语音命令，决定当前 mode / camera 行为
6. 坐标映射到 STM32 控制坐标系
7. RK3588 在 `scan` 状态下生成扫描目标点；`return_home` 由 STM32 按 mode 执行物理回中
8. 通过串口发送到 STM32
9. STM32 接收后按当前 mode 执行底层控制并驱动云台

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
│   │   ├── vision.py            # 视觉兼容包装层
│   │   └── voice/               # v4.0 实时语音模块
│   ├── configs/
│   │   ├── default.yaml         # 基础硬件 / 安全默认配置
│   │   ├── runtime_tracking.yaml # 视觉闭环场景配置
│   │   ├── runtime_voice.yaml   # 语音 + 视觉联调主入口
│   │   └── v3_0.yaml            # 兼容别名，等价转发到 runtime_voice.yaml
│   ├── logs/                    # 运行日志目录
│   ├── models/
│   │   ├── retinaface/          # RetinaFace RKNN 模型目录
│   │   └── asr/                 # SenseVoice / VAD 模型目录（需自行准备）
│   ├── scripts/
│   │   ├── find_devices.sh      # 设备发现脚本
│   │   ├── install_service.sh   # service 安装脚本
│   │   ├── run_headless.sh      # headless 启动脚本
│   │   ├── run_voice.sh         # 语音 + 主程序启动脚本
│   │   ├── test_retinaface_rknn.py # RetinaFace 单图 smoke test
│   │   └── uninstall_service.sh # service 卸载脚本
│   ├── services/
│   │   └── gimbal-ai.service    # systemd service 模板
│   ├── tools/
│   │   └── voice_realtime_test.py # 语音链路独立测试工具
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
sudo apt-get update
sudo apt-get install -y alsa-utils libsndfile1

cd Software_RK3588
python3 -m pip install -r requirements.txt
```

OrangePi / RK3588 板端建议使用单独的 Python 环境，例如 `gimbal` conda 环境或项目虚拟环境。

当前 `requirements.txt` 已包含 v4.0 语音链路需要的 Python 包。安装完成后，建议额外确认环境中能正常导入：

- `numpy`
- `soundfile`
- `sherpa_onnx`

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

当前推荐的配置结构是：

- `configs/default.yaml`
  基础硬件 / detector / runtime 安全默认项
- `configs/runtime_tracking.yaml`
  在 `default.yaml` 基础上打开成熟的视觉闭环行为
- `configs/runtime_voice.yaml`
  在 `runtime_tracking.yaml` 基础上启用实时语音输入

如果要体验当前主程序集成版 v4.0 联调，建议优先使用 `configs/runtime_voice.yaml`，而不是继续直接编辑 `default.yaml`。

`configs/v3_0.yaml` 目前保留为兼容别名，内部会转发到 `configs/runtime_voice.yaml`，这样旧命令不会立即失效。

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

说明：

- 模型文件不随仓库发布，需要用户自行准备
- 若未准备 `.rknn` 模型，可先使用 `haar_face` 路径完成基础联调
- 具体获取与转换步骤请参考上游官方示例说明

### 语音模型说明

当前 v4.0 使用以下语音模型资源：

#### SenseVoice ASR

- 上游项目：`sherpa-onnx`
- 当前使用模型：`sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17`
- 本地目录：
  `Software_RK3588/models/asr/sherpa/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/`
- 目录内关键文件：
  - `model.int8.onnx`
  - `tokens.txt`

说明：

- 当前仓库不直接分发上述模型文件，需要用户自行准备
- 代码默认按上述目录结构查找模型
- 当前离线识别基于 `sherpa_onnx.OfflineRecognizer.from_sense_voice(...)` 调用方式接入

#### Silero VAD

- 上游项目：`Silero VAD`
- 当前使用模型：`silero_vad.onnx`
- 本地路径：
  `Software_RK3588/models/asr/sherpa/silero_vad.onnx`

说明：

- 当前仓库不直接分发该文件，需要用户自行准备
- 主程序集成版 v4.0 使用该 VAD 模型做实时语音段检测

#### 模型获取说明

上述 ASR / VAD 文件建议按上游项目官方发布页面获取，建议优先从上游官方发布页获取与当前 README 中模型名一致的版本，避免因模型版本差异导致目录结构或接口不一致。

#### 许可证说明

语音模型文件及其许可证遵循对应上游项目；当前仓库主要提供工程集成与运行时接入代码，不直接重新分发模型权利本身。

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
python main.py --gui --config configs/runtime_tracking.yaml
```

主程序集成版 v4.0 联调推荐命令：

```bash
cd Software_RK3588
python main.py --gui --config configs/runtime_voice.yaml
```

#### headless 模式

适用场景：无显示器、后台运行或为后续 systemd 托管做验证。

```bash
cd Software_RK3588
python main.py --headless --config configs/runtime_tracking.yaml
```

主程序集成版 v4.0 最小联调命令：

```bash
cd Software_RK3588
python main.py --headless --config configs/runtime_voice.yaml
```

#### `run_headless.sh` 脚本

适用场景：统一的 headless 启动入口，适合手动执行，也适合被 service 调用。

```bash
bash Software_RK3588/scripts/run_headless.sh
```

#### `run_voice.sh` 脚本

适用场景：当前 v4.0 语音 + 视觉主程序集成联调入口，也是最推荐的演示命令。

默认行为：

- 默认补 `--gui`
- 默认补 `--config configs/runtime_voice.yaml`
- 若你自己传了 `--headless` 或 `--config ...`，脚本会尊重你的参数，不重复追加

示例：

```bash
bash Software_RK3588/scripts/run_voice.sh
```

headless 语音联调：

```bash
bash Software_RK3588/scripts/run_voice.sh --headless
```

### 5. 语音链路独立验证

如果你需要单独排查麦克风、VAD、ASR 或命令词解析，可以使用：

```bash
cd Software_RK3588
python -u tools/voice_realtime_test.py --debug
```

如果只想验证离线 wav -> ASR 能力：

```bash
cd Software_RK3588
python scripts/decode_wav.py /path/to/test.wav
```

### 6. 安装 systemd 服务

适用场景：OrangePi / RK3588 长期后台运行。

说明：

- 当前 `install_service.sh` 安装的是保守版 headless service
- 默认启动参数仍使用 `configs/default.yaml`
- 如果你希望 service 直接跑 v4.0 语音版，需要额外调整 `services/gimbal-ai.service` 的 `ExecStart`

```bash
bash Software_RK3588/scripts/install_service.sh
```

卸载：

```bash
bash Software_RK3588/scripts/uninstall_service.sh
```

### 7. 日志查看

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
- 当前语音能力是本地命令词输入，不是自由对话助手
- 当前板端语音演示优先使用 USB 麦克风，板载 MIC 噪声较大
- 当前协议仍是单向主链路，没有下位机状态回传、ACK 或重传机制
- STM32 侧 `scan` 轨迹依然由 RK3588 生成，并未引入独立扫描控制器

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

### 阶段 3：模式闭环与主动搜索

当前已完成的重点包括：

- 最小 mode command 闭环
- `scan` 主动搜索动作
- `return_home` 闭环补齐
- STM32 最小 mode 消费与 OLED 状态显示

### 阶段 4：本地实时语音命令接入

当前已完成的重点包括：

- 实时语音监听线程
- Silero VAD + SenseVoice 离线识别
- 语音命令解析与主线程桥接
- voice override 防抢权
- GUI / headless 主程序集成联调

### 阶段 5：更强感知与协议扩展

后续可继续推进：

- 更细的状态回传 / ACK / 协议增强
- RetinaFace 后端进一步稳定性与部署收口

### 阶段 6：向更完整的桌面级智能体形态扩展

更长期的方向包括：

- 在稳定的感知与控制底座上逐步扩展更丰富的交互与任务调度能力
- 从单一视觉云台系统走向更完整的桌面级嵌入式智能体 / 桌面助手形态

## 第三方模型与来源说明

本项目使用了若干第三方模型/模型转换链路进行工程集成，包括但不限于：

- RetinaFace（RKNN Model Zoo 示例链路）
- SenseVoice（通过 sherpa-onnx 接入）
- Silero VAD

这些模型文件不直接随仓库发布。请使用者根据 README 中的目录说明自行准备模型，并遵循对应上游项目的许可证与使用条款。

## 许可证

本项目遵循 [MIT License](LICENSE)。
