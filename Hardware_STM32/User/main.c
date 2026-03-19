/**
  ******************************************************************************
  * @file    main.c
  * @author  Z-Teddy
  * @brief   主程序入口与 RTOS 任务调度器
  * @note    包含系统初始化、核心控制任务与人机交互任务的实现
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

/* FreeRTOS 头文件 */
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"

/* 硬件库头文件 */
#include "stm32f10x.h"

/* 应用层模块 */
#include "protocol.h"
#include "PID.h"
#include "PWM.h"
#include "OLED.h"
#include "bsp_usart.h"

/* =================================================================================
 * 系统参数配置 (Configuration Macros)
 * ================================================================================= */

/** @brief 图像帧中心坐标 X (基于 RK3588 视觉端分辨率 320x240) */
#define FRAME_CENTER_X   160

/** @brief 图像帧中心坐标 Y (基于 RK3588 视觉端分辨率 320x240) */
#define FRAME_CENTER_Y   120

/** @brief 目标丢失判定超时时间 (ms) */
#define FACE_TIMEOUT_MS  300

#define LINK_TIMEOUT_MS  1500

/** @brief PWM 输出限幅 (单位: us) */
#define PWM_MIN_US       500
#define PWM_MAX_US       2500

/* =================================================================================
 * 全局共享资源 (Shared Resources)
 * ================================================================================= */

/** * @brief  目标跟踪坐标 (Shared between ISR/Task_Control and Task_GUI)
  * @note   使用 volatile 修饰以防止编译器优化，因涉及多任务访问，
  * 在 32 位系统上读写 16 位变量通常是原子的，但在高并发场景下建议使用互斥锁。
  */
static volatile int16_t target_x = FRAME_CENTER_X;
static volatile int16_t target_y = FRAME_CENTER_Y;

/** @brief 最近一次有效人脸数据的系统时间戳 (用于 GUI 状态显示) */
static volatile TickType_t g_last_face_tick = 0;

/* 任务句柄定义 */
TaskHandle_t Task_Control_Handle = NULL;
TaskHandle_t Task_GUI_Handle     = NULL;

/* =================================================================================
 * 辅助工具函数 (Helper Functions)
 * ================================================================================= */

/**
  * @brief  数值范围限制函数 (Clamp)
  * @param  v: 输入值
  * @param  lo: 下限值
  * @param  hi: 上限值
  * @return 限制在 [lo, hi] 区间内的值
  */
static int clamp_int(int v, int lo, int hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static char* AutoMode_To_OLED(void)
{
    if (g_safe_hold_active)
    {
        return "Mode: SAFE ";
    }

    switch (g_AutoMode)
    {
        case AUTO_MODE_HOLD:
            return "Mode: HOLD ";
        case AUTO_MODE_SCAN:
            return "Mode: SCAN ";
        case AUTO_MODE_RETURN_HOME:
            return "Mode: HOME ";
        case AUTO_MODE_TRACK:
        default:
            return "Mode: TRK  ";
    }
}

/* =================================================================================
 * RTOS 任务实现 (Tasks Implementation)
 * ================================================================================= */

/**
  * @brief  核心控制任务 (High Priority)
  * @note   负责协议解析、PID 闭环计算与舵机执行
  * @note   运行频率: 25Hz (周期 40ms)
  * @param  pvParameters: 任务参数 (未使用)
  */
void Task_Control(void *pvParameters)
{
    (void)pvParameters;

    PID_Init();
    PID_Sync_Current_PWM(1500, 1500);

    TickType_t last_face_tick = 0;

    for (;;)
    {
        GimbalCmd_t msg;
        GimbalCmd_t last_msg;
        uint8_t has_new_msg = 0;

        while (xQueueReceive(xCmdQueue, &msg, 0) == pdTRUE)
        {
            last_msg = msg;
            has_new_msg = 1;
        }

        if (has_new_msg)
        {
            switch (last_msg.cmd_id)
            {
                case PROT_CMD_TRACK_FACE:
                {
                    if (g_SystemMode == MODE_AUTO_TRACKING &&
                        (g_AutoMode == AUTO_MODE_TRACK ||
                         g_AutoMode == AUTO_MODE_SCAN))
                    {
                        target_x = (int16_t)clamp_int(last_msg.x, 0, 319);
                        target_y = (int16_t)clamp_int(last_msg.y, 0, 239);
                        g_target_available = 1;
                        last_face_tick = xTaskGetTickCount();
                        g_last_face_tick = last_face_tick;
                    }
                    break;
                }

                case PROT_CMD_SET_ANGLE:
                {
                    int pwm_x;
                    int pwm_y;

                    g_SystemMode = MODE_MANUAL_CMD;

                    pwm_x = 1500 + (int)(last_msg.f_yaw * 11.1f);
                    pwm_y = 1500 + (int)(last_msg.f_pitch * 11.1f);

                    pwm_x = clamp_int(pwm_x, PWM_MIN_US, PWM_MAX_US);
                    pwm_y = clamp_int(pwm_y, PWM_MIN_US, PWM_MAX_US);

                    PWM_SetCompare3((uint16_t)pwm_x);
                    PWM_SetCompare4((uint16_t)pwm_y);
                    PID_Sync_Current_PWM(pwm_x, pwm_y);
                    break;
                }

                case PROT_CMD_SET_EXPRESSION:
                default:
                    break;
            }
        }

        if (g_SystemMode == MODE_AUTO_TRACKING)
        {
            TickType_t now = xTaskGetTickCount();
            TickType_t last_link_tick = g_last_link_tick;

            if (last_link_tick == 0 ||
                (now - last_link_tick) > pdMS_TO_TICKS(LINK_TIMEOUT_MS))
            {
                g_target_available = 0;
                g_safe_hold_active = 1;
            }

            if (g_safe_hold_active)
            {
                /* Safe hold on link timeout */
            }
            else if (g_AutoMode == AUTO_MODE_HOLD)
            {
                g_target_available = 0;
                /* Explicit hold mode keeps current PWM output */
            }
            else if (g_AutoMode == AUTO_MODE_RETURN_HOME)
            {
                g_target_available = 0;
                /* Return-home moves servos back to physical center PWM */
                PID_Move_Towards_Center();
            }
            else if (g_target_available == 0)
            {
                /* Hold current PWM until RK sends new coordinates */
            }
            else if (last_face_tick != 0 &&
                     (now - last_face_tick) > pdMS_TO_TICKS(FACE_TIMEOUT_MS))
            {
                g_target_available = 0;
                /* Coordinate stream timeout falls back to hold */
            }
            else
            {
                pid_S_X((float)target_x, (float)FRAME_CENTER_X);
                pid_S_Y((float)target_y, (float)FRAME_CENTER_Y);
            }
        }

        vTaskDelay(pdMS_TO_TICKS(40));
    }
}

/**
  * @brief  人机交互任务 (Low Priority)
  * @note   负责刷新 OLED 屏幕状态显示
  * @note   运行频率: 约 5Hz (周期 200ms)
  * @param  pvParameters: 任务参数 (未使用)
  */
void Task_GUI(void *pvParameters)
{
    (void)pvParameters;

    OLED_Init();
    OLED_ShowString(1, 1, "System Ready");

    for (;;)
    {
        /* Line 1: 显示当前工作模式 */
        if (g_SystemMode == MODE_AUTO_TRACKING)
            OLED_ShowString(1, 1, AutoMode_To_OLED());
        else
            OLED_ShowString(1, 1, "Mode: VOICE");

        /* Line 2/3: 显示当前目标坐标 */
        OLED_ShowString(2, 1, "X:");
        OLED_ShowSignedNum(2, 3, (int32_t)target_x, 4);

        OLED_ShowString(3, 1, "Y:");
        OLED_ShowSignedNum(3, 3, (int32_t)target_y, 4);

        /* Line 4: 显示视觉目标状态 (OK / LOST) */
        {
            TickType_t now = xTaskGetTickCount();
            TickType_t last = g_last_face_tick;

            if (g_safe_hold_active)
            {
                OLED_ShowString(4, 1, "Face: SAFE");
            }
            else if (last == 0)
            {
                OLED_ShowString(4, 1, "Face: ----"); /* 尚未收到任何数据 */
            }
            else
            {
                uint32_t age_ms = (uint32_t)((now - last) * portTICK_PERIOD_MS);
                
                if (age_ms > FACE_TIMEOUT_MS)
                    OLED_ShowString(4, 1, "Face: LOST");
                else
                    OLED_ShowString(4, 1, "Face:  OK ");
            }
        }

        vTaskDelay(pdMS_TO_TICKS(200));
    }
}

/* =================================================================================
 * 主程序入口
 * ================================================================================= */

/**
  * @brief  Main Function
  * @note   系统硬件初始化 -> RTOS 资源创建 -> 启动调度器
  */
int main(void)
{
    /* 1. 配置中断优先级分组 (FreeRTOS 推荐 Group 4) */
    NVIC_PriorityGroupConfig(NVIC_PriorityGroup_4);

    /* 2. 初始化软件协议栈 (队列、定时器) */
    Protocol_Init();

    /* 3. 初始化硬件外设 */
    USART_Config();
    PWM_Init();

    /* 4. 创建 RTOS 任务 */
    /* 核心控制任务: 优先级 3, 栈大小 512 Words */
    xTaskCreate(Task_Control, "Control", 512, NULL, 3, &Task_Control_Handle);
    
    /* GUI 显示任务: 优先级 1, 栈大小 256 Words */
    xTaskCreate(Task_GUI,     "GUI",     256, NULL, 1, &Task_GUI_Handle);

    /* 5. 启动任务调度器 (永不返回) */
    vTaskStartScheduler();

    /* 正常情况下不会执行到此处 */
    while (1) {}
}
