# RK3588 <-> STM32 通信协议说明

## 1. 文档定位

本文描述当前仓库真实代码中已经落地的 RK3588 -> STM32 最小通信协议，用于说明：

- RK3588 如何向 STM32 发送目标与状态信息
- STM32 当前如何解析并消费这些协议帧
- v1.5 到当前 v2.0 第一轮收口阶段，协议层实际新增了哪些能力

当前协议仍然是单向主链路，主要服务于视觉云台最小闭环，不是完整的双向控制总线，也没有 ACK、序列重传或复杂错误恢复设计。

## 2. 当前阶段能力变化

相对 v1.5，当前 v2.0 第一轮在协议层新增了最小状态化能力：

- 增加 `CMD_HEARTBEAT (0x01)`，用于链路保活
- 增加 `CMD_NO_TARGET (0x05)`，用于显式通知“当前无目标”
- RK3588 侧支持按配置节流发送 heartbeat / no-target
- STM32 侧增加 link timeout 后的最小 safe hold

当前仍未形成的能力包括：

- `CMD_SET_MODE (0x06)` 的完整上下位机模式闭环
- scan 动作闭环
- 下位机回传状态
- ACK / CRC / 重传机制

## 3. 帧格式

当前帧格式由 `Software_RK3588/app/protocol.py` 和 `Hardware_STM32/User/APP/protocol.c` 共同决定：

```text
[HEAD1][HEAD2][CMD][LEN][PAYLOAD...][CHECKSUM]
```

字段说明：

| 字段 | 大小 | 说明 |
| :--- | :--- | :--- |
| `HEAD1` | 1 byte | 固定为 `0xAA` |
| `HEAD2` | 1 byte | 固定为 `0x55` |
| `CMD` | 1 byte | 命令字 |
| `LEN` | 1 byte | payload 长度 |
| `PAYLOAD` | `LEN` bytes | 载荷 |
| `CHECKSUM` | 1 byte | `(CMD + LEN + sum(PAYLOAD)) & 0xFF` |

补充说明：

- 多字节整型与浮点数当前都按小端发送
- STM32 当前解析器要求 `LEN` 范围为 `1..30`
- 因为旧解析器不接受零长度帧，所以 heartbeat 当前使用 2 字节 payload，而不是空载荷

## 4. 当前命令字

| CMD | 名称 | RK3588 当前状态 | STM32 当前状态 |
| :--- | :--- | :--- | :--- |
| `0x01` | `CMD_HEARTBEAT` | 已实现，可按配置发送 | 已实现，刷新链路活跃时间 |
| `0x02` | `CMD_TRACK_FACE` | 已实现，主链路核心命令 | 已实现，进入自动追踪输入 |
| `0x03` | `CMD_SET_ANGLE` | 打包接口保留 | 已实现，作为手动角度控制命令 |
| `0x04` | `CMD_SET_EXPRESSION` | 打包接口保留 | 已实现最小解析 |
| `0x05` | `CMD_NO_TARGET` | 已实现，可按配置发送 | 已实现，进入最小 safe hold 语义 |
| `0x06` | `CMD_SET_MODE` | 打包接口已保留 | 仅保留接收，不驱动完整模式逻辑 |

## 5. 各命令 payload 定义

### 5.1 `CMD_HEARTBEAT = 0x01`

payload 结构：

```text
[seq(uint8)][status_flags(uint8)]
```

说明：

- `seq`：心跳序号，RK3588 侧每次发送后自增并按 `uint8` 回绕
- `status_flags`：状态位预留字段，当前默认发送 `0`

STM32 当前行为：

- 校验 `LEN == 2`
- 刷新 `g_last_link_tick`
- 不触发控制动作

### 5.2 `CMD_TRACK_FACE = 0x02`

payload 结构：

```text
[x(int16_le)][y(int16_le)]
```

说明：

- RK3588 会先把摄像头坐标映射到 STM32 控制坐标系再发送
- 当前默认映射目标范围来自 `serial.stm32_width` / `serial.stm32_height`

STM32 当前行为：

- 校验 `LEN == 4`
- 解析为 `int16` 小端坐标
- 在自动模式下更新 `target_x / target_y`
- 置 `g_target_available = 1`
- 刷新 `g_last_face_tick` 与 `g_last_link_tick`

### 5.3 `CMD_SET_ANGLE = 0x03`

payload 结构：

```text
[yaw(float_le)][pitch(float_le)]
```

说明：

- 当前主要是协议层保留能力
- RK3588 主循环当前未使用这条命令

STM32 当前行为：

- 校验 `LEN == 8`
- 解析为两个小端 `float`
- 切到手动角度控制语义
- 刷新 link 活跃时间

### 5.4 `CMD_SET_EXPRESSION = 0x04`

payload 结构：

```text
[face_id(uint8)]
```

说明：

- RK3588 当前仅保留封装接口，主循环未使用
- STM32 当前保留最小解析入口

### 5.5 `CMD_NO_TARGET = 0x05`

payload 结构：

```text
[reason(uint8)]
```

当前 reason 定义来自 `Software_RK3588/app/protocol.py`：

| 值 | 名称 | 含义 |
| :--- | :--- | :--- |
| `0x00` | `NO_TARGET_REASON_LOST` | 正常检测丢失 |
| `0x01` | `NO_TARGET_REASON_CAMERA` | 摄像头侧异常预留 |
| `0x02` | `NO_TARGET_REASON_DETECTOR` | 检测器侧异常预留 |

STM32 当前行为：

- 校验 `LEN == 1`
- 记录最近一次 no-target reason
- 置 `g_target_available = 0`
- 刷新 `g_last_link_tick`
- 后续控制任务进入最小 safe hold

### 5.6 `CMD_SET_MODE = 0x06`

payload 结构：

```text
[mode(uint8)]
```

当前 mode 枚举来自 RK3588 协议封装：

| 值 | 名称 |
| :--- | :--- |
| `0x00` | `track` |
| `0x01` | `hold` |
| `0x02` | `return_home` |
| `0x03` | `scan` |

当前状态：

- RK3588 侧已有 `pack_mode()`
- STM32 侧仅保留接收入口并刷新链路活跃时间
- 当前版本没有依赖该命令完成主功能

## 6. RK3588 当前发送行为

当前行为由 `Software_RK3588/main.py` 与 `Software_RK3588/app/serial_ctrl.py` 决定：

- `CMD_TRACK_FACE`
  当 detector 输出目标且状态机允许进入 `track` 时发送
- `CMD_HEARTBEAT`
  主循环每轮都会调用 `send_heartbeat()`，但只有 `protocol.heartbeat_enabled=true` 且达到节流间隔时才真的发送
- `CMD_NO_TARGET`
  仅在进入 no-target 分支时按节流发送；默认 `protocol.no_target_enabled=false`
- `CMD_SET_MODE`
  当前主循环未使用
- `CMD_SET_ANGLE` / `CMD_SET_EXPRESSION`
  当前主循环未使用，属于保留接口

默认配置下：

- `heartbeat_enabled = false`
- `no_target_enabled = false`
- `mode_command_enabled = false`

因此默认行为仍尽量接近 v1.5，只是在主循环内部已经具备 v2.0 最小状态机和去抖逻辑。

## 7. STM32 当前消费行为

当前行为由 `Hardware_STM32/User/APP/protocol.c` 与 `Hardware_STM32/User/main.c` 决定。

### 7.1 heartbeat

- 收到合法 heartbeat 后只刷新链路活跃时间
- 不改变 PID 目标
- 不强制切模式

### 7.2 no-target

- 收到合法 no-target 后将 `g_target_available` 置 `0`
- 控制任务在自动模式下停止继续按旧目标做 PID 推动
- 当前 safe 行为是 hold 当前输出，而不是主动 scan 或复杂归位

### 7.3 link timeout

当前 STM32 还保留两层保护：

- `FACE_TIMEOUT_MS = 300`
  目标长时间没有新的 track 坐标时，进入 hold
- `LINK_TIMEOUT_MS = 1500`
  整条链路长时间没有有效 heartbeat / target / no-target / 其它合法包时，进入 safe hold

当前 `LINK_TIMEOUT_MS` 更像兜底保护，而不是代替 face timeout。

### 7.4 当前 safe hold 语义

当前 safe hold 的实际语义是：

- 不继续基于旧目标推进 PID
- 保持当前 PWM / 云台姿态
- 不自动触发 scan
- 不自动形成完整 return-home 策略

## 8. 当前限制与后续方向

当前仍有限制：

- `CMD_SET_MODE` 仅是预留接口，不是完整模式控制闭环
- `scan` 还没有真实动作实现
- 协议仍是单向主链路，没有下位机回传
- 校验仍是简单字节和，不是 CRC
- 没有 ACK / 重传 / 序列同步机制

后续如果继续扩展，可以考虑：

- 将 mode command 真正接入上下位机控制链路
- 增加更清晰的状态遥测或最小回传
- 按需要升级校验方式
- 在不破坏当前最小闭环的前提下逐步扩展更多 detector 或控制模式
