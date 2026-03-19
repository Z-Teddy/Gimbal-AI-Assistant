/**
  ******************************************************************************
  * @file    PID.h
  * @author  Z-Teddy
  * @brief   位置式PID控制算法头文件
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#ifndef __PID_H
#define __PID_H

#include "stm32f10x.h"

/**
  * @brief  PID 控制器初始化
  * @note   复位误差累积，准备开始控制
  */
void PID_Init(void);

/**
  * @brief  复位积分器 (Anti-windup 辅助)
  * @note   建议在模式切换或长时间待机后调用
  */
void PID_Reset_Integrator(void);

/**
  * @brief  X轴 (Yaw) PID 计算更新
  * @param  true_S: 当前实际角度/PWM值
  * @param  tar_S:  目标角度/PWM值
  */
void pid_S_X(float true_S, float tar_S);

/**
  * @brief  Y轴 (Pitch) PID 计算更新
  * @param  true_S: 当前实际角度/PWM值
  * @param  tar_S:  目标角度/PWM值
  */
void pid_S_Y(float true_S, float tar_S);

/**
  * @brief  同步 PID 内部状态与实际 PWM 值
  * @note   用于从手动模式切换回自动模式时的平滑过渡
  * @param  pwm_x: 当前 X 轴 PWM 值
  * @param  pwm_y: 当前 Y 轴 PWM 值
  */
void PID_Sync_Current_PWM(int pwm_x, int pwm_y);

/**
  * @brief  平滑驱动双轴 PWM 回到物理中位
  * @note   用于 AUTO_MODE_RETURN_HOME，避免把“回中”误当作视觉坐标闭环
  */
void PID_Move_Towards_Center(void);

#endif
