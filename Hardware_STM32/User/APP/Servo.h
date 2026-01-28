/**
  ******************************************************************************
  * @file    Servo.h
  * @author  Z-Teddy
  * @brief   舵机控制应用层头文件
  * @note    提供角度设置与回读接口 (封装了 PWM 脉宽转换计算)
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#ifndef _SERVO_H
#define _SERVO_H

#include "stm32f10x.h"

/* =================================================================================
 * 舵机机械限位参数 (单位: 度)
 * ================================================================================= */

#define MIN_ANGLE_X 0       /*!< Angle1 (Y轴/Pitch) 最小角度 */
#define MAX_ANGLE_X 180     /*!< Angle1 (Y轴/Pitch) 最大角度 */

#define MIN_ANGLE_Y 0       /*!< Angle2 (X轴/Yaw)   最小角度 */
#define MAX_ANGLE_Y 180     /*!< Angle2 (X轴/Yaw)   最大角度 */

/* =================================================================================
 * 控制接口函数
 * ================================================================================= */

/**
  * @brief  舵机控制初始化
  */
void Servo_Init(void);

/**
  * @brief  设置 Angle1 (Y轴/俯仰)
  * @note   对应 PWM 通道 4 (PA3)
  * @param  Angle1: 目标角度 (0~180)
  */
void Servo_SetAngle1(float Angle1);

/**
  * @brief  设置 Angle2 (X轴/偏航)
  * @note   对应 PWM 通道 3 (PA2)
  * @param  Angle2: 目标角度 (0~180)
  */
void Servo_SetAngle2(float Angle2);

/* =================================================================================
 * 状态回读接口
 * ================================================================================= */

/**
  * @brief  获取 PWM 通道 4 (Y轴) 当前比较值
  * @retval CCR4 寄存器值
  */
uint16_t PWM_GetCompare4(void); 

/**
  * @brief  获取 PWM 通道 3 (X轴) 当前比较值
  * @retval CCR3 寄存器值
  */
uint16_t PWM_GetCompare3(void); 

/**
  * @brief  读取 Angle1 当前实际角度 (Y轴)
  * @retval 反解后的角度值 (float)
  */
float ReadServoAngle1(void);

/**
  * @brief  读取 Angle2 当前实际角度 (X轴)
  * @retval 反解后的角度值 (float)
  */
float ReadServoAngle2(void);

#endif
