# Changelog

## v4.0 - 实时语音命令主程序集成版

### 新增
- 新增 `Software_RK3588/app/voice/` 模块，包含 SenseVoice 离线识别封装、Silero VAD、命令词解析、运行时桥接与 override 控制
- 新增本地实时语音输入链路：`USB 麦克风 -> VAD -> ASR -> VoiceCommand -> 主线程队列 -> 现有 runtime`
- 新增 `Software_RK3588/tools/voice_realtime_test.py`，用于语音链路独立排障与联调
- 新增 `Software_RK3588/scripts/run_voice.sh`，作为语音 + 视觉主程序集成入口
- 新增 `Software_RK3588/configs/runtime_voice.yaml`，用于 v4.0 GUI / headless 联调与演示

### 改进
- 语音线程已接入 `main.py` 主运行时，GUI / headless 两种模式均可使用
- 语音命令通过线程安全队列交回主线程消费，不再维护第二套平行 runtime
- 新增 `voice override` 机制，避免 `TRACK / HOLD / SCAN / HOME` 被自动状态机立即抢回
- 修复语音监听退出竞态，Ctrl+C 后不再残留 `arecord` 进程或出现 `NoneType.poll` traceback
- 增加语音联调能力：chunk / RMS / VAD 状态日志、segment 调试落盘、GUI 中的 Voice 状态显示
- 配置结构升级为“基础配置 + 场景配置”，主推荐入口改为 `configs/runtime_tracking.yaml` 与 `configs/runtime_voice.yaml`

### 兼容性
- 保留 `configs/v3_0.yaml` 作为兼容别名，内部转发到 `configs/runtime_voice.yaml`
- 保留 `scripts/decode_wav.py`、`scripts/quick_asr_test.sh`、`tools/voice_realtime_test.py` 作为独立验证入口
- 语音输入没有引入新的串口协议，仍复用既有 `CMD_SET_MODE` / `send_mode()` 主链路

### 当前版本定位
v4.0 在 v3.0 视觉模式闭环与主动搜索基础上，把系统推进到“视觉 + 本地实时语音命令双输入”的异构嵌入式交互原型。

## v3.0 - 模式闭环与主动搜索原型

### 新增
- 补齐 `track / hold / scan / return_home` 四态最小 mode command 闭环
- RK3588 在主循环内实现真实 `scan` 行为，按时间生成左右往返扫描目标点
- `return_home` 从一次性发 home 坐标升级为短时持续发送 home 坐标
- 新增 `configs/v3_0.yaml`，用于 v3.0 联调与演示

### 改进
- RK3588 保持 `read -> detect -> send -> display` 主链不变，只在现有状态机基础上扩展主动搜索链路
- STM32 新增最小 auto mode 消费：`TRACK / HOLD / SCAN / HOME`，并在 OLED 上显示 `TRK / HOLD / SCAN / HOME / VOICE / SAFE`
- `HOLD` 获得真实语义：停止 PID 推进并保持当前姿态
- 串口重连后可通过 mode 周期重发完成最小状态重同步

### 当前版本定位
v3.0 在现有 `haar_face / retinaface / RKNNLite / NPU` 感知基础上，把系统从“最小异构视觉云台”推进到了“具备模式闭环和主动搜索行为的异构嵌入式系统原型”。

## v2.5 - RetinaFace detector 接入

### 新增
- 新增 `retinaface` detector，支持与 `haar_face` 通过 `detector.type` 切换
- 接入基于 RK3588 NPU / RKNNLite 的 `RetinaFace_mobile320.rknn`
- 新增 RetinaFace 后处理模块与单图 smoke test 脚本

### 改进
- 感知层从单一 Haar detector 扩展为双 detector 配置
- 保持现有 GUI / headless 主程序入口兼容
- 保持状态机与串口主链路兼容

### 验证
- 单图 smoke test 通过
- 主程序 GUI / headless 联调通过
- `track / hold` 基本状态切换正常

## v2.0 - 最小状态化异构系统原型与第一轮收口

### 新增
- 增加 `detector` / `protocol` / `control` 配置骨架
- 增加 heartbeat / no-target 协议封装与发送入口
- 增加主循环最小模式状态机：`track / hold / return_home`
- 增加主循环去抖 / 滞回机制，降低瞬时漏检导致的模式抖动
- 完成 detector 模块化第一轮，新增 `app/detectors/` 目录与 `DetectionResult` 统一结果结构
- STM32 增加 heartbeat / no-target / link-timeout safe hold 的最小协议接线
- 新增 `scripts/install_service.sh`
- 新增 `scripts/uninstall_service.sh`
- 新增 `scripts/find_devices.sh`
- 新增 `docs/communication_protocol.md`

### 改进
- `main.py` 不再直接硬耦合 Haar 实现，默认仍通过 `detector.type = "haar_face"` 保持当前行为
- RK3588 与 STM32 已形成最小双端状态闭环
- README / deployment / architecture 文档已同步到当前真实代码状态

### 当前版本定位
当前版本不再只是 v1.5 的工程化基线，而是已经推进到具备最小状态、模式、保护和 detector 扩展骨架的 v2.0 第一轮原型。默认行为仍尽量兼容 v1.5，但已经具备继续向更完整嵌入式智能体形态演进的工程底座。

## v1.5 - RK3588 Linux 侧第一轮工程化基线

### 新增
- 支持 YAML 配置加载
- 增加 logging（控制台 + 文件）
- 支持 GUI / headless 双模式运行
- 增加 camera recovery
- 增加 serial reconnect
- 新增 `scripts/run_headless.sh`
- 新增 `services/gimbal-ai.service` 模板
- 新增 `docs/system_architecture.md`
- 新增 `docs/deployment_orangepi.md`

### 改进
- 将 recovery 配置正式纳入 `settings.py` 校验链
- README 重构，明确项目长期目标与当前阶段定位

### 当前版本定位
当前版本聚焦 RK3588 Linux 侧第一轮工程化能力建设，为后续更强感知、交互与桌面级嵌入式智能体扩展打底。
