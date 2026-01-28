/**
  ******************************************************************************
  * @file    PWM.h
  * @author  Z-Teddy
  * @brief   PWM驱动模块头文件
  * @note    负责配置 TIM2 输出 PWM 波形以控制舵机
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#ifndef _PWM_H
#define _PWM_H

#include "stm32f10x.h"

/**
  * @brief  PWM 初始化
  * @note   配置 TIM2 时基与输出通道 (PA2, PA3)
  */
void PWM_Init(void);

/**
  * @brief  设置 Y 轴 (Pitch) PWM 比较值
  * @note   对应引脚: PA3 (TIM2_CH4)
  * @param  Compare: 比较值 (500~2500)
  */
void PWM_SetCompare4(uint16_t Compare);

/**
  * @brief  设置 X 轴 (Yaw) PWM 比较值
  * @note   对应引脚: PA2 (TIM2_CH3)
  * @param  Compare: 比较值 (500~2500)
  */
void PWM_SetCompare3(uint16_t Compare);

#endif
