/**
  ******************************************************************************
  * @file    Servo.c
  * @author  Z-Teddy
  * @brief   舵机角度控制层 (将角度转换为 PWM 脉宽)
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#include "stm32f10x.h"
#include "PWM.h" 
#include "Servo.h"

/**
  * @brief  舵机控制初始化
  * @note   实际调用 PWM 底层初始化
  */
void Servo_Init(void)
{
    PWM_Init();
}

/**
  * @brief  设置 Y 轴角度 (俯仰 Pitch)
  * @note   对应引脚: PA3 (TIM2_CH4)
  * @param  Angle1: 目标角度 (0.0 ~ 180.0)
  */
void Servo_SetAngle1(float Angle1)
{
    /* 角度限幅 (防止机械卡死) */
    Angle1 = (Angle1 > MAX_ANGLE_X) ? MAX_ANGLE_X : ((Angle1 < MIN_ANGLE_X) ? MIN_ANGLE_X : Angle1);
    
    /* 角度转 PWM 脉宽 (500~2500us) */
    /* 调用 PWM 通道 4 */
    PWM_SetCompare4((uint16_t)(Angle1 / 180 * 2000 + 500));
}

/**
  * @brief  设置 X 轴角度 (偏航 Yaw)
  * @note   对应引脚: PA2 (TIM2_CH3)
  * @param  Angle2: 目标角度 (0.0 ~ 180.0)
  */
void Servo_SetAngle2(float Angle2)
{
    /* 角度限幅 */
    Angle2 = (Angle2 > MAX_ANGLE_Y) ? MAX_ANGLE_Y : ((Angle2 < MIN_ANGLE_Y) ? MIN_ANGLE_Y : Angle2);
    
    /* 角度转 PWM 脉宽 */
    /* 调用 PWM 通道 3 */
    PWM_SetCompare3((uint16_t)(Angle2 / 180 * 2000 + 500));
}

/* =================================================================================
 * 状态回读函数
 * ================================================================================= */

/**
  * @brief  获取 Y 轴当前 PWM 寄存器值
  */
uint16_t PWM_GetCompare4(void)  
{  
    return (uint16_t)(TIM2->CCR4);  
}

/**
  * @brief  获取 X 轴当前 PWM 寄存器值
  */
uint16_t PWM_GetCompare3(void)  
{  
    return (uint16_t)(TIM2->CCR3);  
}

/**
  * @brief  读取 Y 轴当前角度 (反解)
  * @retval 当前角度值 (float)
  */
float ReadServoAngle1(void)  
{  
    uint16_t pwmValue = PWM_GetCompare4(); 
    /* 反解公式: (PWM - 500) / 2000 * 180 */
    float angle = (pwmValue - 500) / 2000.0f * 180; 
    return angle;  
}  

/**
  * @brief  读取 X 轴当前角度 (反解)
  * @retval 当前角度值 (float)
  */
float ReadServoAngle2(void)  
{  
    uint16_t pwmValue = PWM_GetCompare3(); 
    /* 反解公式 */
    float angle = (pwmValue - 500) / 2000.0f * 180; 
    return angle;  
}
