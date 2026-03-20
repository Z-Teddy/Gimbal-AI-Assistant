# 系统架构说明

## 1. 文档目的

本文用于说明当前项目的系统组成、数据流、控制流以及 `Software_RK3588` 的软件结构，重点描述当前已经落地的 v4.0 视觉闭环、主动搜索、实时语音命令与双端协同能力。

本文基于当前仓库真实代码与真实目录结构撰写，不把后续规划写成既成事实。

## 2. 项目定位

当前项目可以概括为：

**基于 RK3588 + STM32 的异构嵌入式视觉云台系统。**

其中，RK3588 / OrangePi 侧负责视觉感知与上层运行控制，STM32 侧负责接收目标坐标并执行底层控制。

## 3. 系统总体组成

系统当前由以下部分构成：

- RK3588 / OrangePi
  运行 Linux 侧视觉程序与语音线程，负责图像采集、人脸检测、语音识别、坐标生成、日志和运行管理
- STM32
  接收 RK3588 发来的目标坐标，并执行底层控制逻辑
- 摄像头
  提供输入图像
- USB 麦克风
  提供本地实时语音命令输入
- 串口链路
  负责 RK3588 与 STM32 之间的坐标通信
- 云台执行端
  根据 STM32 的控制结果执行运动

## 4. RK3588 与 STM32 的职责划分

### 4.1 RK3588 / OrangePi 负责

- 摄像头采集
- detector 模块化入口与当前默认 Haar 人脸检测
- 最大人脸目标筛选
- 目标中心坐标生成
- 视觉坐标到 STM32 控制坐标的映射
- 最小模式状态机（`track / hold / scan / return_home`）
- 主循环去抖 / 滞回
- scan 轨迹生成与 return_home 模式驱动
- 实时语音线程（USB 麦克风采集、VAD、ASR、命令词解析）
- 将语音命令通过线程安全队列交回主线程消费
- 语音 override 控制，短时保护语音 mode 命令不被自动状态机立即覆盖
- 按当前协议格式打包并通过串口发送目标坐标、heartbeat、no-target、mode command
- YAML 配置加载
- logging
- 摄像头自动恢复
- 串口自动重连
- headless 启动脚本、systemd 模板与安装/卸载脚本

### 4.2 STM32 负责

- 接收 RK3588 发来的协议帧
- 解析目标坐标
- 处理 heartbeat / no-target / mode command / link-timeout 的最小状态接线
- 执行下位机控制逻辑
- 驱动云台执行端动作

当前文档不展开 STM32 侧代码细节，也不把 RK3588 侧未实现的能力归到 STM32 或反过来混写。

## 5. 数据流 / 控制流说明

当前系统的基本链路如下：

1. 摄像头采集图像帧
2. RK3588 通过 detector 工厂选择当前视觉后端
3. 对单帧执行检测，并从结果中选择当前主目标
4. 语音线程并行执行 `USB 麦克风 -> VAD -> ASR -> VoiceCommand`
5. 主线程统一消费视觉状态与语音命令，判定当前应处于 `track / hold / scan / return_home`
6. 将视觉坐标映射到 STM32 使用的控制坐标系
7. 在 `scan` 状态下由 RK3588 生成扫描目标点；在 `return_home` 状态下由 STM32 执行本地物理回中
8. 打包为串口协议帧
9. 通过串口发送给 STM32
10. STM32 接收后根据当前 mode 消费坐标，或进入最小 safe hold

## 6. 当前主链路

当前 `Software_RK3588` 的主流程仍然保持为：

```text
read -> detect -> send -> display
```

这里的含义是：

- `read`
  从摄像头读取当前帧
- `detect`
  执行人脸检测并生成目标中心点
- `send`
  将目标坐标映射后通过串口发送给 STM32
- `display`
  在 GUI 模式下显示处理后的图像

当前版本在不推翻主链路顺序的前提下，已经补上：

- 配置化
- 日志化
- gui / headless 双模式
- camera recovery
- serial reconnect
- detector 模块化第一轮
- 最小模式状态机
- 主循环去抖 / 滞回
- heartbeat / no-target / link-timeout safe hold
- mode command 最小闭环
- 实时语音命令输入
- 语音线程到主线程的桥接消费
- voice override 防抢权
- systemd 安装/卸载脚本
- 设备发现脚本与协议文档

## 7. `Software_RK3588` 软件结构说明

### 7.1 `main.py`

主程序入口，负责：

- 解析 `--gui`、`--headless`、`--config`
- 加载配置
- 初始化 logging
- 创建视觉、串口、摄像头管理对象
- 在启用 `voice.enabled` 时创建语音监听线程与主线程桥接
- 维持主循环与最小模式状态机
- 在主循环中消费语音命令并应用到现有 runtime
- 在 `scan` 状态下生成并发送扫描坐标
- 在 GUI 模式下显示画面
- 在退出时释放资源

当前主循环的顺序没有被大规模重写，仍保持原有链路。

### 7.2 `config.py`

当前作为 YAML 配置兼容层使用：

- 默认加载 `configs/default.yaml`
- 将 YAML 中的配置同步为模块级常量
- 为仍然依赖旧常量风格的模块提供兼容接口

### 7.3 `app/detectors/` 与 `app/vision.py`

当前视觉层已经完成 detector 模块化第一轮：

- `app/detectors/base.py`
  定义 `BaseDetector` 与统一的 `DetectionResult`
- `app/detectors/haar_detector.py`
  当前默认 Haar 检测实现
- `app/detectors/rknn_retinaface.py`
  RK3588 NPU / RKNNLite RetinaFace 实现
- `app/detectors/retinaface_postprocess.py`
  RetinaFace 后处理、anchor / decode / NMS 逻辑
- `app/detectors/__init__.py`
  提供 `create_detector(settings)` 工厂
- `app/vision.py`
  保留兼容包装层，避免旧调用方式立即失效

当前仓库已落地两个真实 detector：

- `haar_face`
  适合作为基础兼容路径与轻量验证路径
- `retinaface`
  适合作为当前 v4.0 推荐的人脸检测后端

### 7.4 `app/serial_ctrl.py`

负责串口发送与串口连接管理：

- 初始化串口连接
- 控制发送频率
- 执行坐标映射
- 调用协议封装发送坐标、heartbeat、no-target、mode command
- 发送失败后断开并进入重连状态
- 周期性按固定间隔尝试自动重连

当前没有改变坐标映射公式的核心语义，但已经扩展出最小协议状态化与 mode 同步发送入口。

### 7.5 `app/camera_manager.py`

负责摄像头生命周期管理：

- 打开摄像头
- 配置分辨率
- 读取单帧
- 统计连续读帧失败次数
- 达到阈值后释放旧摄像头
- 按固定间隔尝试自动重连

它的目标是提供最小但可用的 camera recovery，而不是复杂设备状态机。

### 7.6 `app/settings.py`

负责 YAML 配置加载与基础校验：

- 读取配置文件
- 与默认配置合并
- 校验当前已使用配置字段的基础类型和取值范围
- 输出给 `config.py` 使用

### 7.7 `app/logging_setup.py`

负责统一初始化 logging：

- 输出到控制台
- 输出到 `logs/` 下的日志文件
- 统一日志级别、格式和时间格式

### 7.8 `configs/default.yaml`

当前默认配置文件，管理以下内容：

- camera 参数
- serial 参数
- detector 参数
- protocol 参数
- control 参数
- runtime 参数
- logging 参数
- voice 参数

它是当前运行参数的主要入口。

### 7.8.1 `configs/runtime_tracking.yaml`

额外提供了成熟视觉闭环场景配置，用于：

- 通过 `extends: default.yaml` 继承当前默认硬件与 detector 配置
- 打开 `heartbeat / no-target / mode command`
- 启用 `scan`
- 提供 `hold_before_scan_sec`、`scan_timeout_sec`、`return_home_hold_sec`、`scan_period_sec`、`scan_offset_px` 等最小参数

### 7.8.2 `configs/runtime_voice.yaml`

在 `runtime_tracking.yaml` 基础上进一步打开 `voice.enabled`，用于当前语音 + 视觉主程序集成联调。

该配置当前还包含：

- USB 麦克风关键字
- 语音 cooldown
- `max_speech_sec`、`vad_threshold`、`min_speech_sec`、`silence_sec`
- `input_gain`
- `voice.override.track_sec / hold_sec / scan_sec / home_sec`

### 7.9 `scripts/run_headless.sh`

当前 headless 启动脚本，负责：

- 切换到正确工作目录
- 优先选择项目虚拟环境 Python
- 明确传入 `--headless`
- 明确传入 `--config configs/default.yaml`

它是当前手动 headless 运行和后续 service 调用的统一入口。

### 7.10 `services/gimbal-ai.service`

当前的 systemd service 模板与安装脚本，负责为长期托管运行提供最小可用部署入口：

- service 模板提供可替换占位符
- `install_service.sh` 负责填充用户、路径和 Python 解释器
- 以 headless 模式运行
- 开启自动重启
- 兼容 journald

## 8. 当前工程化能力

当前 `Software_RK3588` 已经落地的工程化能力包括：

- 配置化
  通过 YAML 管理 camera / serial / detector / protocol / control / runtime / logging 参数
- 日志化
  同时输出到控制台与文件
- gui / headless 双模式
  适配本地调试与后台运行
- camera recovery
  摄像头读帧失败后自动释放并重连
- serial reconnect
  串口初始化失败或发送失败后自动尝试重连
- detector 模块化
  默认 Haar 后端已抽离到独立目录
- 最小状态化
  主循环已具备模式切换、去抖 / 滞回、主动搜索与最小 no-target 策略
- 本地实时语音输入
  USB 麦克风、VAD、离线 ASR、命令词解析、主线程桥接与 override 保护
- 双端状态闭环
  STM32 已接上 heartbeat / no-target / mode command / link-timeout safe hold
- 部署收口
  提供 `run_headless.sh`、service 安装/卸载脚本和设备发现脚本

这些能力的目标是提升运行稳定性、部署可用性和后续扩展余量，而不是一次性重做整套架构。

## 9. 设计边界说明

当前版本明确保持了以下边界：

- 协议只做到最小状态化，没有复杂 ACK / 重传 / 双向回传
- detector 只完成模块化结构，没有引入重依赖或第二个模型
- 当前默认检测算法仍是 Haar，最大人脸选择逻辑未改变
- 未改变主流程的基本顺序
- 协议仍然保持单向最小链路，没有 ACK / 状态回传
- STM32 不负责生成 scan 轨迹，scan 目标点仍由 RK3588 生成

## 10. 当前架构优势

从当前代码状态看，这一版架构的优势主要在于：

- 在不推翻原有业务链路的前提下，补上了配置、日志、状态机和部署入口
- GUI 调试与 headless 运行可以共用一套主程序
- 摄像头和串口的异常不再直接导致进程退出
- 默认 detector 行为保持稳定，同时后续扩展第二个 detector 的改动面已经缩小
- 协议状态化已经把“目标坐标链路”推进到“最小状态链路”
- 目录规模仍然较小，便于个人项目持续迭代
- `config.py` 兼容层降低了从硬编码常量迁移到 YAML 配置的改动成本

## 11. 当前限制与后续方向

### 11.1 当前限制

- 摄像头当前依赖固定 `camera.index`
- 串口当前依赖固定 `serial.port`
- 设备发现当前只做到脚本提示，不做运行时自动绑定
- 当前视觉算法仍是传统 OpenCV Haar Cascade
- 当前仅有一个实际 detector 实现
- 当前仍没有 ACK / 回传协议
- 当前部署脚本是最小 systemd 安装方案，不是复杂运维框架

### 11.2 后续方向

以下内容属于后续可扩展方向，不代表当前已经完成：

- 第二个 detector 接入与切换验证
- 更完整的模式命令闭环和状态回传
- 更稳定的设备发现机制
- 更完善的状态监控与异常统计
- 更强的人脸检测或加速推理方案，例如后续再评估 RKNN 路线
