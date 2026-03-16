# OrangePi / RK3588 端部署与运行说明

## 1. 文档目的

本文用于说明当前仓库中 `Software_RK3588` 目录的部署、配置、启动、systemd 托管、设备发现和日志查看方式。

本文只描述当前仓库已经真实落地的能力，不把后续规划写成已完成项。

## 2. 当前适用范围

- 仅适用于 `Software_RK3588`
- 适用于当前 v2.0 第一轮收口后的 RK3588 部署方式
- 不覆盖 `Hardware_STM32/` 的烧录或下位机调试细节

## 3. 目录位置说明

`Software_RK3588` 当前关键文件如下：

- `Software_RK3588/main.py`
  RK3588 侧主程序入口，支持 `--gui`、`--headless`、`--config`
- `Software_RK3588/config.py`
  YAML 配置兼容层，对旧模块继续暴露常量
- `Software_RK3588/configs/default.yaml`
  默认配置文件
- `Software_RK3588/app/detectors/`
  detector 模块化目录，当前默认后端为 Haar
- `Software_RK3588/app/vision.py`
  视觉兼容包装层
- `Software_RK3588/app/camera_manager.py`
  摄像头打开、读帧、自动恢复
- `Software_RK3588/app/serial_ctrl.py`
  串口发送、heartbeat/no-target 节流与自动重连
- `Software_RK3588/app/settings.py`
  YAML 加载与基础校验
- `Software_RK3588/scripts/run_headless.sh`
  headless 启动脚本
- `Software_RK3588/scripts/install_service.sh`
  systemd 服务安装脚本
- `Software_RK3588/scripts/uninstall_service.sh`
  systemd 服务卸载脚本
- `Software_RK3588/scripts/find_devices.sh`
  设备发现与配置提示脚本
- `Software_RK3588/services/gimbal-ai.service`
  systemd service 模板
- `Software_RK3588/logs/rk3588_tracker.log`
  当前默认日志文件

## 4. 环境准备

### 4.1 Python 环境

当前项目使用 Python 运行，`scripts/run_headless.sh` 与 `scripts/install_service.sh` 的解释器选择顺序如下：

1. `Software_RK3588/.venv/bin/python`
2. `Software_RK3588/venv/bin/python`
3. 系统 `python3`

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
- 串口设备需要与 `configs/default.yaml` 中的 `serial.port` 一致
- STM32 侧串口波特率需要与 `serial.baud_rate` 保持一致，当前默认值为 `115200`

## 5. 设备发现与配置

在修改配置之前，建议先执行：

```bash
bash Software_RK3588/scripts/find_devices.sh
```

脚本会枚举并打印：

- `/dev/video*`
- `/dev/v4l/by-id/*`
- `/dev/ttyUSB*`
- `/dev/ttyACM*`
- `/dev/serial/by-id/*`

并给出推荐填写到 `configs/default.yaml` 的值。

当前建议：

- `camera.index` 仍填写数值索引
- `serial.port` 优先使用 `/dev/serial/by-id/*`

## 6. 配置文件说明

当前默认配置文件为：

```text
Software_RK3588/configs/default.yaml
```

当前配置已扩展为以下几类：

- `camera`
  摄像头索引、分辨率、翻转方式、读帧失败阈值、重连间隔
- `serial`
  串口设备路径、波特率、STM32 侧坐标范围、发送节流、重连间隔
- `detector`
  当前 detector 类型，默认 `haar_face`
- `protocol`
  heartbeat、no-target、mode command 等协议侧开关
- `control`
  最小模式状态机、去抖 / 滞回、归位参数
- `runtime`
  默认运行模式、窗口名、GUI 显示环境
- `logging`
  日志级别、日志目录、日志文件名、日志格式

### 6.1 当前最关键的参数

部署阶段最常需要调整的参数通常是：

- `camera.index`
- `camera.width` / `camera.height`
- `camera.flip`
- `serial.port`
- `serial.baud_rate`
- `detector.type`
- `protocol.heartbeat_enabled`
- `protocol.no_target_enabled`
- `control.no_target_mode`
- `runtime.mode`

如果只做最小闭环验证，建议先保留默认控制参数，只根据实际硬件改 `camera.index` 与 `serial.port`。

## 7. 启动方式

### 7.1 GUI 模式启动

在 `Software_RK3588` 目录下执行：

```bash
python main.py --gui --config configs/default.yaml
```

适合本地调试、观察检测框和状态切换。

### 7.2 headless 模式启动

在 `Software_RK3588` 目录下执行：

```bash
python main.py --headless --config configs/default.yaml
```

适合无显示器或后台运行。

### 7.3 `run_headless.sh` 的作用

当前仓库提供了：

```text
Software_RK3588/scripts/run_headless.sh
```

该脚本会：

- 自动进入正确的 `Software_RK3588` 工作目录
- 优先选择项目虚拟环境 Python
- 显式以 `--headless` 模式启动
- 显式使用 `configs/default.yaml`

手动启动命令：

```bash
bash Software_RK3588/scripts/run_headless.sh
```

## 8. systemd 服务安装与卸载

### 8.1 安装方案

当前 `install_service.sh` 采用 **systemd 系统服务** 方案，而不是 `systemctl --user` 方案。

这样做的原因是：

- 更适合 OrangePi / RK3588 这类长期通电的嵌入式运行场景
- 不依赖用户 session 或 `linger`
- 仍通过 `User=` 指定普通用户运行，不要求主进程长期以 root 身份工作

安装命令：

```bash
bash Software_RK3588/scripts/install_service.sh
```

脚本会自动：

- 解析仓库根目录与 `Software_RK3588` 工作目录
- 选择 Python 解释器（优先 `.venv` / `venv`，否则系统 `python3`）
- 填充 `gimbal-ai.service` 模板中的用户、路径和 Python 启动项
- 安装到 `/etc/systemd/system/gimbal-ai.service`
- 执行 `daemon-reload`
- 执行 `enable`
- 执行 `restart`

### 8.2 卸载

```bash
bash Software_RK3588/scripts/uninstall_service.sh
```

脚本会：

- `stop`
- `disable`
- 删除 `/etc/systemd/system/gimbal-ai.service`
- `daemon-reload`

它不会删除仓库内容、日志目录或配置文件。

### 8.3 查看服务状态

```bash
sudo systemctl status gimbal-ai.service --no-pager
sudo journalctl -u gimbal-ai.service -n 100 --no-pager
sudo journalctl -u gimbal-ai.service -f
```

## 9. 日志查看

### 9.1 控制台日志

程序手动启动后，日志会输出到控制台，适合开发阶段和联调时观察。

### 9.2 文件日志

当前日志模块会同时写入文件，默认路径为：

```text
Software_RK3588/logs/rk3588_tracker.log
```

查看方式：

```bash
tail -f Software_RK3588/logs/rk3588_tracker.log
```

### 9.3 systemd 日志

如果通过 service 运行，建议同时看 journald：

```bash
sudo journalctl -u gimbal-ai.service -f
```

## 10. 当前已实现的恢复机制

### 10.1 camera recovery

当前实现了最小但可用的摄像头自动恢复机制：

- 单次读帧失败时记录 warning
- 连续失败达到阈值后释放当前 `cv2.VideoCapture`
- 按配置间隔自动尝试重新打开摄像头
- 恢复成功后继续进入主循环

### 10.2 serial reconnect

当前实现了最小但可用的串口自动重连机制：

- 初始化失败时不把串口功能永久判死
- 发送失败时关闭当前串口连接并进入断开状态
- 主循环持续运行
- 后台按固定时间间隔自动尝试重连
- 重连成功后，在后续仍有目标发送需求时恢复坐标与状态包发送

## 11. 推荐部署流程

建议的最小部署步骤如下：

1. 烧录并确认 STM32 固件正常运行
2. 在 OrangePi / RK3588 上安装 Python 依赖
3. 运行 `find_devices.sh`，确认摄像头与串口
4. 修改 `configs/default.yaml` 中的 `camera.index` 和 `serial.port`
5. 先用 GUI 模式做一次本地验证
6. 再用 `run_headless.sh` 验证 headless 运行
7. 最后执行 `install_service.sh` 安装后台服务

## 12. 最小运行验证

建议至少验证以下场景：

- GUI 模式下能看到目标框和中心点
- headless 模式下程序可持续运行
- 有目标时 STM32 正常追踪
- 丢目标后能进入 hold
- 开启 heartbeat 后无明显副作用
- 串口短暂断开后，serial reconnect 与 camera recovery 仍能恢复主链路

## 13. 常见注意事项

### 13.1 GUI 与 headless 的区别

- GUI 模式会显示 OpenCV 窗口，适合开发和本地调试
- headless 模式不显示窗口，适合后台长期运行或 systemd 托管
- 即使 `configs/default.yaml` 中默认模式为 `gui`，只要命令行显式传入 `--headless`，程序仍会按 headless 模式启动

### 13.2 固定 camera index / fixed serial port 的当前限制

当前实现仍依赖固定设备标识：

- 摄像头使用固定 `camera.index`
- 串口使用固定 `serial.port`

`find_devices.sh` 只能帮助发现和提示，不会自动改配置，也不会在运行时自动热切换设备。

## 14. 当前已知限制

- 摄像头自动恢复当前基于固定索引，不做运行时自动重绑定
- 串口自动重连当前基于固定设备路径，不做自动发现与自动切换
- 当前 detector 默认仍为 OpenCV Haar Cascade
- `scan` 当前仅保留占位
- `CMD_SET_MODE` 当前仅预留，不是完整模式闭环
- 当前部署脚本采用最小 systemd 安装方案，不包含更复杂的环境探测或多实例管理
