/**
  ******************************************************************************
  * @file    protocol.c
  * @author  Z-Teddy
  * @brief   串口通信协议解析层 (Frame Parser & Dispatcher)
  * @note    负责处理串口字节流，解析数据帧并分发至 FreeRTOS 任务队列
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

/* FreeRTOS 头文件引用 */
/* 必须确保 FreeRTOS.h 在 timers.h 等其他组件之前被引用 */
#include "FreeRTOS.h"
#include "task.h"
#include "timers.h"
#include "queue.h"

/* 项目头文件 */
#include "protocol.h"
#include "PID.h"

/* =================================================================================
 * 全局变量定义
 * ================================================================================= */

/** @brief 系统当前运行模式 (默认为自动追踪) */
SystemMode_t g_SystemMode = MODE_AUTO_TRACKING;

volatile AutoMode_t g_AutoMode = AUTO_MODE_TRACK;

/** @brief 云台控制指令消息队列句柄 */
QueueHandle_t xCmdQueue = NULL;

/** @brief 自动回归模式定时器句柄 (看门狗机制) */
TimerHandle_t xAutoRestoreTimer = NULL;

volatile TickType_t g_last_link_tick = 0;
volatile uint8_t g_target_available = 0;
volatile uint8_t g_last_no_target_reason = 0;
volatile uint8_t g_safe_hold_active = 0;

/* =================================================================================
 * 内部静态变量 (协议解析状态机上下文)
 * ================================================================================= */
static uint8_t rx_state = 0;      /*!< 状态机当前状态 */
static uint8_t rx_cmd = 0;        /*!< 当前解析的命令字 */
static uint8_t rx_len = 0;        /*!< 当前帧的数据长度 */
static uint8_t rx_cnt = 0;        /*!< 数据接收计数器 */
static uint8_t rx_buffer[32];     /*!< 数据接收缓冲区 */
static uint8_t rx_checksum = 0;   /*!< 校验和累加器 */

static void Protocol_Mark_Link_Alive_ISR(void)
{
    g_last_link_tick = xTaskGetTickCountFromISR();
    g_safe_hold_active = 0;
}

static uint8_t Protocol_Is_Valid_Auto_Mode(uint8_t raw_mode)
{
    return raw_mode <= (uint8_t)AUTO_MODE_SCAN;
}

/* =================================================================================
 * 辅助函数
 * ================================================================================= */

/**
  * @brief  软件定时器回调：自动回归逻辑
  * @param  xTimer 定时器句柄
  * @note   当系统在指定时间内未收到外部强控指令时，触发此回调以恢复自动追踪模式
  */
void vAutoRestoreCallback(TimerHandle_t xTimer)
{
    if (g_SystemMode == MODE_MANUAL_CMD)
    {
        g_SystemMode = MODE_AUTO_TRACKING;
        
        /* 模式切换时重置 PID 积分项，防止积分饱和导致的控制突变 */
        PID_Reset_Integrator(); 
    }
}

/**
  * @brief  将 4 字节缓冲区转换为 float 类型 (IEEE 754)
  * @param  buf 指向包含 4 字节数据的缓冲区指针 (小端模式)
  * @return 转换后的浮点数值
  */
float Buffer_To_Float(uint8_t* buf)
{
    float result;
    /* 通过指针强转实现内存重新解释 (注意：需确保字节对齐安全) */
    uint8_t* p = (uint8_t*)&result;
    p[0] = buf[0]; 
    p[1] = buf[1]; 
    p[2] = buf[2]; 
    p[3] = buf[3];
    return result;
}

/* =================================================================================
 * 核心接口函数
 * ================================================================================= */

/**
  * @brief  通信协议栈初始化
  * @note   初始化消息队列、软件定时器等 FreeRTOS 资源
  */
void Protocol_Init(void)
{
    /* 创建指令消息队列，深度为 5 */
    xCmdQueue = xQueueCreate(5, sizeof(GimbalCmd_t));

    g_last_link_tick = 0;
    g_target_available = 0;
    g_last_no_target_reason = 0;
    g_safe_hold_active = 0;
    g_AutoMode = AUTO_MODE_TRACK;
    
    /* 创建自动回归定时器：3000ms 周期，单次触发 (One-shot) */
    xAutoRestoreTimer = xTimerCreate("AutoRestore", 
                                     pdMS_TO_TICKS(3000), 
                                     pdFALSE, 
                                     (void*)0, 
                                     vAutoRestoreCallback);
}

/**
  * @brief  处理已通过校验的完整数据帧
  * @note   此函数在 ISR (中断) 上下文中运行，禁止调用阻塞式 API
  */
static void Protocol_Packet_Finished(void)
{
    GimbalCmd_t msg;
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;

    msg.cmd_id = rx_cmd;

    switch (rx_cmd)
    {
        case PROT_CMD_HEARTBEAT: /* 0x01: heartbeat */
            if (rx_len != 2)
            {
                return;
            }
            Protocol_Mark_Link_Alive_ISR();
            return;

        case PROT_CMD_TRACK_FACE: /* 0x02: 人脸坐标数据包 */
            if (rx_len != 4)
            {
                return;
            }
            msg.x = (int16_t)(rx_buffer[0] | (rx_buffer[1] << 8));
            msg.y = (int16_t)(rx_buffer[2] | (rx_buffer[3] << 8));
            Protocol_Mark_Link_Alive_ISR();
            break;

        case PROT_CMD_SET_ANGLE: /* 0x03: 角度控制数据包 (语音强控) */
            if (rx_len != 8)
            {
                return;
            }
            msg.f_yaw   = Buffer_To_Float(&rx_buffer[0]);
            msg.f_pitch = Buffer_To_Float(&rx_buffer[4]);
            Protocol_Mark_Link_Alive_ISR();
            
            /* 收到有效控制指令，重置自动回归定时器 (喂狗) */
            if (xAutoRestoreTimer != NULL)
            {
                /* 根据当前上下文选择正确的 API */
                if (xPortIsInsideInterrupt())
                {
                    xTimerResetFromISR(xAutoRestoreTimer, &xHigherPriorityTaskWoken);
                }
                else
                {
                    /* 理论上不应在此处触发，但保留以防调用上下文改变 */
                    xTimerReset(xAutoRestoreTimer, 0); 
                }
            }
            break;

        case PROT_CMD_SET_EXPRESSION: /* 0x04: 表情控制数据包 */
            if (rx_len != 1)
            {
                return;
            }
            msg.face_id = rx_buffer[0];
            Protocol_Mark_Link_Alive_ISR();
            break;

        case PROT_CMD_NO_TARGET: /* 0x05: no target */
            if (rx_len != 1)
            {
                return;
            }
            g_target_available = 0;
            g_last_no_target_reason = rx_buffer[0];
            g_AutoMode = AUTO_MODE_HOLD;
            Protocol_Mark_Link_Alive_ISR();
            return;

        case PROT_CMD_SET_MODE: /* 0x06: set auto mode */
            if (rx_len != 1)
            {
                return;
            }
            if (!Protocol_Is_Valid_Auto_Mode(rx_buffer[0]))
            {
                return;
            }
            g_AutoMode = (AutoMode_t)rx_buffer[0];
            if (g_AutoMode == AUTO_MODE_HOLD ||
                g_AutoMode == AUTO_MODE_RETURN_HOME)
            {
                g_target_available = 0;
            }
            Protocol_Mark_Link_Alive_ISR();
            return;

        default: 
            return; /* 未知指令，直接返回 */
    }

    /* 将解析完成的消息推入队列 */
    if (xCmdQueue != NULL)
    {
        xQueueSendFromISR(xCmdQueue, &msg, &xHigherPriorityTaskWoken);
    }
    
    /* 如果唤醒了更高优先级的任务，请求上下文切换 */
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}

/**
  * @brief  串口字节流解析状态机 (FSM)
  * @param  byte 接收到的单字节数据
  * @note   需在串口接收中断 (USARTx_IRQHandler) 中调用此函数
  */
void Protocol_ParseByte_ISR(uint8_t byte)
{
    switch (rx_state)
    {
        case 0: /* 状态 0: 寻找帧头 1 (0xAA) */
            if (byte == 0xAA) 
            { 
                rx_state = 1; 
                rx_checksum = 0; 
            }
            break;
            
        case 1: /* 状态 1: 寻找帧头 2 (0x55) */
            if (byte == 0x55) 
            {
                rx_state = 2;
            }
            else 
            {
                rx_state = 0; /* 帧头不匹配，重置状态 */
            }
            break;
            
        case 2: /* 状态 2: 读取命令字 (CMD) */
            rx_cmd = byte;
            rx_checksum += byte;
            rx_state = 3;
            break;
            
        case 3: /* 状态 3: 读取数据长度 (LEN) */
            rx_len = byte;
            rx_checksum += byte;
            rx_cnt = 0;
            
            /* 安全检查：验证数据长度是否合法 */
            /* 限制最大长度以防止缓冲区溢出 (Max: 30 bytes) */
            if (rx_len == 0 || rx_len > 30)
            { 
                rx_state = 0;   /* 长度异常，丢弃当前帧并重置 */
                rx_checksum = 0;
            }
            else
            {
                rx_state = 4;   /* 长度合法，进入数据接收状态 */
            }
            break;
            
        case 4: /* 状态 4: 读取数据载荷 (Payload) */
            rx_buffer[rx_cnt++] = byte;
            rx_checksum += byte;
            
            if (rx_cnt >= rx_len) 
            {
                rx_state = 5;
            }
            break;
            
        case 5: /* 状态 5: 校验和比对 (Checksum) */
            if (byte == (rx_checksum & 0xFF))
            {
                /* 校验通过，处理完整数据包 */
                Protocol_Packet_Finished();
            }
            /* 无论校验是否通过，处理完一帧后重置状态机以接收下一帧 */
            rx_state = 0;
            break;
            
        default: 
            rx_state = 0; 
            break;
    }
}
