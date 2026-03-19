/**
  ******************************************************************************
  * @file    protocol.h
  * @author  Z-Teddy
  * @brief   通信协议定义头文件 (指令、模式与数据结构)
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#ifndef __PROTOCOL_H
#define __PROTOCOL_H

#include "stm32f10x.h"
#include "FreeRTOS.h"
#include "queue.h"

/* =================================================================================
 * 协议指令常量 (Command IDs)
 * ================================================================================= */
#define PROT_CMD_HEARTBEAT      0x01    /*!< Command: heartbeat */
#define PROT_CMD_TRACK_FACE     0x02    /*!< Command: track face */
#define PROT_CMD_SET_ANGLE      0x03    /*!< Command: set absolute angle */
#define PROT_CMD_SET_EXPRESSION 0x04    /*!< Command: set expression */
#define PROT_CMD_NO_TARGET      0x05    /*!< Command: no target */
#define PROT_CMD_SET_MODE       0x06    /*!< Command: set mode (reserved) */

/* =================================================================================
 * 系统数据类型定义
 * ================================================================================= */

/** * @brief 系统运行模式枚举
  */
typedef enum {
    MODE_AUTO_TRACKING = 0, /*!< 自动模式：视觉 PID 闭环跟踪 */
    MODE_MANUAL_CMD    = 1  /*!< 手动模式：响应语音/外部指令强控 */
} SystemMode_t;

typedef enum {
    AUTO_MODE_TRACK       = 0, /*!< RK 正常跟踪 */
    AUTO_MODE_HOLD        = 1, /*!< 保持当前姿态 */
    AUTO_MODE_RETURN_HOME = 2, /*!< 回到 home 坐标 */
    AUTO_MODE_SCAN        = 3  /*!< RK 下发扫描轨迹 */
} AutoMode_t;

/** * @brief 云台控制指令结构体 (消息队列载荷)
  * @note  这是一个通用载荷结构，根据 cmd_id 读取对应的字段
  */
typedef struct {
    uint8_t  cmd_id;    /*!< 指令 ID (决定包类型) */
    
    /* 追踪模式数据 (PROT_CMD_TRACK_FACE) */
    int16_t  x;         /*!< 目标 X 坐标 */
    int16_t  y;         /*!< 目标 Y 坐标 */
    
    /* 角度控制模式数据 (PROT_CMD_SET_ANGLE) */
    float    f_yaw;     /*!< 目标偏航角 (Yaw) */
    float    f_pitch;   /*!< 目标俯仰角 (Pitch) */
    
    /* 表情控制模式数据 (PROT_CMD_SET_EXPRESSION) */
    uint8_t  face_id;   /*!< 表情 ID 索引 */
} GimbalCmd_t;

/* =================================================================================
 * 导出变量与函数接口
 * ================================================================================= */

/* 全局状态变量 */
extern SystemMode_t g_SystemMode;   /*!< 当前系统工作模式 */
extern volatile AutoMode_t g_AutoMode;           /*!< 当前 auto mode 子状态 */
extern QueueHandle_t xCmdQueue;     /*!< 指令消息队列句柄 */
extern volatile TickType_t g_last_link_tick;      /*!< Last valid link activity tick */
extern volatile uint8_t g_target_available;       /*!< 1 when target packets are active */
extern volatile uint8_t g_last_no_target_reason;  /*!< Last no-target reason code */
extern volatile uint8_t g_safe_hold_active;       /*!< 1 when link timeout safe hold is active */

/**
  * @brief  协议栈初始化
  * @note   创建队列与定时器资源
  */
void Protocol_Init(void);

/**
  * @brief  串口字节流解析状态机
  * @note   需在串口接收中断 (ISR) 中调用
  * @param  byte: 接收到的单字节数据
  */
void Protocol_ParseByte_ISR(uint8_t byte);

#endif
