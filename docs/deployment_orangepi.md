# OrangePi / RK3588 端部署与运行说明

## 1. 文档目的

本文用于说明当前仓库中 `Software_RK3588` 目录的部署、配置、启动和日志查看方式，适合作为 OrangePi / RK3588 端的第一轮工程化运行说明。

本文只描述当前仓库已经实际落地的能力，不把后续规划写成已完成项。

## 2. 当前适用范围

- 仅适用于 `Software_RK3588`
- 适用于当前分支下已经完成的 RK3588 Linux 侧工程化版本
- 不覆盖 `Hardware_STM32/` 的烧录、调试或协议开发细节

## 3. 目录位置说明

`Software_RK3588` 当前关键文件如下：

- `Software_RK3588/main.py`
  RK3588 侧主程序入口，支持 `--gui`、`--headless`、`--config`
- `Software_RK3588/config.py`
  YAML 配置兼容层，对旧模块继续暴露常量
- `Software_RK3588/configs/default.yaml`
  默认配置文件
- `Software_RK3588/app/vision.py`
  人脸检测与画面标注
- `Software_RK3588/app/camera_manager.py`
  摄像头打开、读帧、自动恢复
- `Software_RK3588/app/serial_ctrl.py`
  串口发送与自动重连
- `Software_RK3588/app/settings.py`
  YAML 加载与基础校验
- `Software_RK3588/app/logging_setup.py`
  日志初始化
- `Software_RK3588/scripts/run_headless.sh`
  headless 启动脚本
- `Software_RK3588/services/gimbal-ai.service`
  systemd service 模板
- `Software_RK3588/logs/rk3588_tracker.log`
  当前默认日志文件

## 4. 环境准备

### 4.1 Python 环境

当前项目使用 Python 运行，启动脚本 `scripts/run_headless.sh` 的解释器选择顺序如下：

1. `Software_RK3588/.venv/bin/python`
2. `Software_RK3588/venv/bin/python`
3. 系统 `python3`
4. 系统 `python`

如果已经为项目准备了虚拟环境，建议优先使用项目目录下的虚拟环境。

### 4.2 依赖安装

进入 `Software_RK3588` 后安装依赖：

```bash
cd Software_RK3588
python3 -m pip install -r requirements.txt
```

当前 Python 侧运行依赖以 `requirements.txt` 为准，典型依赖包括：

- `opencv-python`
- `pyserial`
- `PyYAML`

### 4.3 摄像头与串口设备要求

- 摄像头需要能被当前 Linux 系统识别，并能通过 OpenCV 的 `cv2.VideoCapture(index)` 打开
- 串口设备需要与 `configs/default.yaml` 中的 `serial.port` 一致，当前默认值为 `/dev/ttyUSB0` ，实际部署时应以系统识别到的设备节点为准。
- STM32 侧串口波特率需要与 `serial.baud_rate` 保持一致，当前默认值为 `115200`

## 5. 配置文件说明

当前默认配置文件为：

```text
Software_RK3588/configs/default.yaml
```

该文件目前包含四类配置：

- `camera`
  摄像头索引、分辨率、翻转方式、读帧失败阈值、重连间隔
- `serial`
  串口设备路径、波特率、STM32 侧坐标范围、发送节流、重连间隔
- `runtime`
  默认运行模式、窗口名、GUI 显示环境
- `logging`
  日志级别、日志目录、日志文件名、日志格式

### 5.1 当前最关键的参数

部署阶段最常需要调整的参数通常是以下几项：

- `camera.index`
  摄像头设备索引
- `camera.width` / `camera.height`
  摄像头采集分辨率
- `camera.flip`
  画面翻转方式
- `camera.max_read_failures`
  连续读帧失败阈值
- `camera.reconnect_interval_sec`
  摄像头自动重连间隔
- `serial.port`
  串口设备路径
- `serial.baud_rate`
  串口波特率
- `serial.reconnect_interval_sec`
  串口自动重连间隔
- `runtime.mode`
  默认运行模式，当前默认值为 `gui`
- `logging.log_dir`
  日志目录，当前默认值为 `logs`

## 6. 启动方式

### 6.1 GUI 模式启动

在 `Software_RK3588` 目录下执行：

```bash
python main.py --gui --config configs/default.yaml
```

当前分支中，GUI 模式已经实际验证可正常启动。

### 6.2 headless 模式启动

在 `Software_RK3588` 目录下执行：

```bash
python main.py --headless --config configs/default.yaml
```

当前分支中，headless 模式已经实际验证可正常启动。

### 6.3 `run_headless.sh` 的作用

当前仓库提供了：

```text
Software_RK3588/scripts/run_headless.sh
```

该脚本的作用是：

- 自动进入正确的 `Software_RK3588` 工作目录
- 优先选择项目虚拟环境 Python
- 显式以 `--headless` 模式启动
- 显式使用 `configs/default.yaml`

手动启动命令：

```bash
bash Software_RK3588/scripts/run_headless.sh
```

当前分支中，`scripts/run_headless.sh` 已手动验证可以正常启动程序。

## 7. 日志查看

### 7.1 控制台日志

程序启动后，日志会输出到控制台，适合开发阶段和手动运行时观察。

### 7.2 文件日志

当前日志模块会同时写入文件，默认路径为：

```text
Software_RK3588/logs/rk3588_tracker.log
```

查看方式：

```bash
tail -f Software_RK3588/logs/rk3588_tracker.log
```

## 8. 当前已实现的恢复机制

### 8.1 camera recovery

当前实现了最小但可用的摄像头自动恢复机制：

- 单次读帧失败时记录 warning
- 连续失败达到阈值后释放当前 `cv2.VideoCapture`
- 按配置间隔自动尝试重新打开摄像头
- 恢复成功后继续进入主循环

当前分支中，camera recovery 已经做过热插拔验证。

需要注意的是，这一机制的目标是提高运行稳定性，不代表已经覆盖所有摄像头驱动或硬件异常场景。

### 8.2 serial reconnect

当前实现了最小但可用的串口自动重连机制：

- 初始化失败时不把串口功能永久判死
- 发送失败时关闭当前串口连接并进入断开状态
- 主循环持续运行
- 后台按固定时间间隔自动尝试重连
- 重连成功后，在后续继续产生目标发送请求时恢复正常坐标发送。

当前分支中，serial reconnect 已经做过断开恢复验证。

需要注意的是，这一机制主要覆盖“设备暂时断开后重新连回”的场景，并不等于完整的串口状态机。

## 9. `gimbal-ai.service` 模板说明

当前仓库提供了：

```text
Software_RK3588/services/gimbal-ai.service
```

它当前是一个 **模板文件**，用于为后续 systemd 托管做准备，不表示已经在系统中正式安装或启用。

该模板当前的设计特点：

- `WorkingDirectory` 指向 `Software_RK3588`
- `ExecStart` 调用 `scripts/run_headless.sh`
- 默认以 headless 模式运行
- `Restart=always`
- 输出兼容 journald

在实际使用前，需要替换至少以下字段：

- `User=USER_NAME`
- `WorkingDirectory=/abs/path/to/.../Software_RK3588`
- `ExecStart=/abs/path/to/.../Software_RK3588/scripts/run_headless.sh`

## 10. 常见问题 / 注意事项

### 10.1 GUI 与 headless 的区别

- GUI 模式会显示 OpenCV 窗口，适合开发和本地调试
- headless 模式不显示窗口，适合后台长期运行或 systemd 托管
- 即使 `configs/default.yaml` 中默认模式为 `gui`，只要命令行显式传入 `--headless`，程序仍会按 headless 模式启动

### 10.2 USB 设备热插拔可能引起的现象

- 摄像头热插拔后，程序会经历短暂的读帧失败和重连等待
- 串口设备断开后，如果这时仍有目标发送请求，会先触发发送失败日志，然后进入重连流程
- 这些恢复行为会同时出现在控制台日志和文件日志中
- 在当前实际测试中，串口设备拔插过程中可能伴随 USB 总线层面的扰动，进而导致摄像头短暂失稳并触发 camera recovery。这类现象更接近底层 USB/供电/枚举行为，不等同于业务逻辑错误。

### 10.3 固定 camera index / fixed serial port 的当前限制

当前实现仍依赖固定设备标识：

- 摄像头使用固定 `camera.index`
- 串口使用固定 `serial.port`

如果热插拔后设备编号变化，例如：

- 摄像头索引不再是原来的值
- 串口设备从 `/dev/ttyUSB0` 变成了其他路径

那么当前版本不会自动发现新设备，只会按原配置继续重试。

## 11. 当前已知限制

- 摄像头自动恢复当前基于固定索引，不做设备枚举
- 串口自动重连当前基于固定设备路径，不做动态发现
- 当前视觉算法仍为 OpenCV Haar Cascade，人脸检测能力受环境光、姿态和距离影响
- 当前 systemd 部署仍停留在模板准备阶段，未包含自动安装与启用流程
- 当前日志以“控制台 + 文件”双通道输出为主，尚未做更复杂的日志轮转策略
- `gimbal-ai.service` 当前仅提供模板，尚未在仓库中包含自动安装、自动替换路径或自动启用脚本。

## 12. 后续可扩展方向

以下内容属于后续计划，不代表当前已经实现：

- 更稳定的设备发现机制，例如通过固定设备别名或 udev 规则降低索引/端口漂移影响
- 更细化的参数说明与部署示例
- 更完整的 systemd 部署脚本与安装流程
- 更强的人脸检测模型或更高性能的推理方案
- 更细化的运行状态监控与异常统计
