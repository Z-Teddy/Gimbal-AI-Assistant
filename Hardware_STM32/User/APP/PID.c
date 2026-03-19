/**
  ******************************************************************************
  * @file    PID.c
  * @author  Z-Teddy
  * @brief   位置式PID控制算法实现 (带死区控制与平滑限幅)
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#include "stm32f10x.h"
#include "PWM.h"
#include "OLED.h"
#include "PID.h"

/* =================================================================================
 * 调参宏定义区
 * ================================================================================= */

/* 死区阈值：误差在此范围内忽略不计，防止舵机高频抖动 */
#define PID_DEAD_ZONE       5.0f

/* 爬坡限制 (Slew Rate Limit)：每次控制周期 PWM 允许变化的最大数值 */
/* 值越小越平滑但响应慢，值越大响应快但易抖动 */
#define PID_MAX_STEP        45.0f

/* 舵机 PWM 物理限幅 */
#define SERVO_PWM_MAX       2500.0f
#define SERVO_PWM_MIN       500.0f
#define SERVO_PWM_CENTER    1500.0f

/* =================================================================================
 * 全局变量定义
 * ================================================================================= */

/* 记录舵机当前停留的 PWM 值 */
float Current_PWM_X = 1550.0f;
float Current_PWM_Y = 1500.0f;

/* 上次误差记录 */
float last_Err_S_X = 0.0f;
float last_Err_S_Y = 0.0f;

/* PID 参数配置 */
/* X轴 (左右/Yaw) */
static const float Kp_X = -0.05f;
static const float Kd_X = -1.45f;

/* Y轴 (俯仰/Pitch) */
static const float Kp_Y =  0.05f;
static const float Kd_Y =  1.45f;

/* =================================================================================
 * PID 算法实现
 * ================================================================================= */

/**
  * @brief  Y轴 PID 计算 (俯仰 Pitch)
  * @note   对应舵机通道 PA3
  * @param  true_val: 当前实际值
  * @param  target_val: 目标设定值
  */
void pid_S_Y(float true_val, float target_val)
{
    /* 计算误差 */
    float error = target_val - true_val;
    
    /* 1. 死区控制 (Deadband Control) */
    /* 防止在目标点附近因传感器噪声导致的微小震荡 */
    if (error > -PID_DEAD_ZONE && error < PID_DEAD_ZONE)
    {
        error = 0.0f;
    }
    
    /* 2. PD 算法计算 (计算理论增量) */
    float delta = (Kp_Y * error) + (Kd_Y * (error - last_Err_S_Y));
    
    /* 3. 输出平滑限制 (Slew Rate Limiter) */
    /* 限制单次调整幅度，消除云台顿挫感 */
    if (delta > PID_MAX_STEP) 
    {
        delta = PID_MAX_STEP;
    } 
    else if (delta < -PID_MAX_STEP) 
    {
        delta = -PID_MAX_STEP;
    }

    /* 4. 更新状态 */
    last_Err_S_Y = error;           /* 更新上次误差 */
    Current_PWM_Y += delta;         /* 累加平滑后的增量 */
    
    /* 5. 物理输出限幅 (Safety Saturation) */
    if (Current_PWM_Y > SERVO_PWM_MAX) Current_PWM_Y = SERVO_PWM_MAX;
    if (Current_PWM_Y < SERVO_PWM_MIN) Current_PWM_Y = SERVO_PWM_MIN;
    
    /* 6. 执行输出 */
    PWM_SetCompare4((uint16_t)Current_PWM_Y);
}

/**
  * @brief  X轴 PID 计算 (偏航 Yaw)
  * @note   对应舵机通道 PA2
  * @param  true_val: 当前实际值
  * @param  target_val: 目标设定值
  */
void pid_S_X(float true_val, float target_val)
{
    /* 计算误差 */
    float error = target_val - true_val;
    
    /* 1. 死区控制 */
    if (error > -PID_DEAD_ZONE && error < PID_DEAD_ZONE)
    {
        error = 0.0f;
    }

    /* 2. PD 算法计算 */
    float delta = (Kp_X * error) + (Kd_X * (error - last_Err_S_X));
    
    /* 3. 输出平滑限制 */
    if (delta > PID_MAX_STEP) 
    {
        delta = PID_MAX_STEP;
    } 
    else if (delta < -PID_MAX_STEP) 
    {
        delta = -PID_MAX_STEP;
    }
    
    /* 4. 更新状态 */
    last_Err_S_X = error;
    Current_PWM_X += delta;
    
    /* 5. 物理输出限幅 */
    if (Current_PWM_X > SERVO_PWM_MAX) Current_PWM_X = SERVO_PWM_MAX;
    if (Current_PWM_X < SERVO_PWM_MIN) Current_PWM_X = SERVO_PWM_MIN;
    
    /* 6. 执行输出 */
    PWM_SetCompare3((uint16_t)Current_PWM_X);
}

/* =================================================================================
 * 辅助控制函数
 * ================================================================================= */

/**
  * @brief  复位 PID 积分项与误差记录
  * @note   建议在模式切换时调用
  */
void PID_Reset_Integrator(void)
{
    last_Err_S_X = 0.0f;
    last_Err_S_Y = 0.0f;
}

/**
  * @brief  初始化 PID 模块
  */
void PID_Init(void)
{
    PID_Reset_Integrator();
}

/**
  * @brief  同步 PID 内部状态与实际 PWM 值
  * @note   当从手动模式切换回自动模式时，必须调用此函数，
  * 将 PID 的内部当前值对齐到舵机实际位置，防止跳变。
  * @param  pwm_x: 当前 X 轴 PWM 值
  * @param  pwm_y: 当前 Y 轴 PWM 值
  */
void PID_Sync_Current_PWM(int pwm_x, int pwm_y)
{
    Current_PWM_X = (float)pwm_x;
    Current_PWM_Y = (float)pwm_y;
}

/**
  * @brief  平滑驱动双轴 PWM 回到物理中位
  * @note   使用与 PID 相同的爬坡限制，避免回中动作突跳
  */
void PID_Move_Towards_Center(void)
{
    float delta_x = SERVO_PWM_CENTER - Current_PWM_X;
    float delta_y = SERVO_PWM_CENTER - Current_PWM_Y;

    if (delta_x > PID_MAX_STEP)
    {
        delta_x = PID_MAX_STEP;
    }
    else if (delta_x < -PID_MAX_STEP)
    {
        delta_x = -PID_MAX_STEP;
    }

    if (delta_y > PID_MAX_STEP)
    {
        delta_y = PID_MAX_STEP;
    }
    else if (delta_y < -PID_MAX_STEP)
    {
        delta_y = -PID_MAX_STEP;
    }

    if (delta_x > -1.0f && delta_x < 1.0f)
    {
        Current_PWM_X = SERVO_PWM_CENTER;
    }
    else
    {
        Current_PWM_X += delta_x;
    }

    if (delta_y > -1.0f && delta_y < 1.0f)
    {
        Current_PWM_Y = SERVO_PWM_CENTER;
    }
    else
    {
        Current_PWM_Y += delta_y;
    }

    if (Current_PWM_X > SERVO_PWM_MAX) Current_PWM_X = SERVO_PWM_MAX;
    if (Current_PWM_X < SERVO_PWM_MIN) Current_PWM_X = SERVO_PWM_MIN;
    if (Current_PWM_Y > SERVO_PWM_MAX) Current_PWM_Y = SERVO_PWM_MAX;
    if (Current_PWM_Y < SERVO_PWM_MIN) Current_PWM_Y = SERVO_PWM_MIN;

    last_Err_S_X = 0.0f;
    last_Err_S_Y = 0.0f;

    PWM_SetCompare3((uint16_t)Current_PWM_X);
    PWM_SetCompare4((uint16_t)Current_PWM_Y);
}
