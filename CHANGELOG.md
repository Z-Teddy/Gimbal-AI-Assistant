# Changelog

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
