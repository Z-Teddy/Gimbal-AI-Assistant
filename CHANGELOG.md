# Changelog

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