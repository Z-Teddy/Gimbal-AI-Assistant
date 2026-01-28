/**
  ******************************************************************************
  * @file    PWM.c
  * @author  Z-Teddy
  * @brief   舵机PWM输出配置 (TIM2 CH3/CH4)
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#include "stm32f10x.h"
#include "PWM.h"

/**
  * @brief  PWM 初始化函数
  * @note   配置 TIM2 输出 50Hz PWM 波形
  * @note   X轴: PA2 (TIM2_CH3), Y轴: PA3 (TIM2_CH4)
  */
void PWM_Init(void)
{
    /* 1. 开启 TIM2 和 GPIOA 时钟 */
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM2, ENABLE);
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
    
    /* 2. 配置 GPIO */
    GPIO_InitTypeDef GPIO_InitStructure;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP; /* 复用推挽输出 */
    
    /* 使用 PA2 (X轴) 和 PA3 (Y轴) */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_2 | GPIO_Pin_3; 
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &GPIO_InitStructure);
    
    /* 3. 配置时基 (50Hz) */
    TIM_InternalClockConfig(TIM2);
    
    TIM_TimeBaseInitTypeDef TIM_TimeBaseInitStructure;
    TIM_TimeBaseInitStructure.TIM_ClockDivision = TIM_CKD_DIV1;
    TIM_TimeBaseInitStructure.TIM_CounterMode = TIM_CounterMode_Up;
    
    /* ARR (20ms): 20000计数 * 1us = 20ms */
    TIM_TimeBaseInitStructure.TIM_Period = 20000 - 1;   
    
    /* PSC (1us): 72MHz / 72 = 1MHz */
    TIM_TimeBaseInitStructure.TIM_Prescaler = 72 - 1;   
    
    TIM_TimeBaseInitStructure.TIM_RepetitionCounter = 0;
    TIM_TimeBaseInit(TIM2, &TIM_TimeBaseInitStructure);
    
    /* 4. 配置 PWM 输出通道 */
    TIM_OCInitTypeDef TIM_OCInitStructure;
    TIM_OCStructInit(&TIM_OCInitStructure);
    TIM_OCInitStructure.TIM_OCMode = TIM_OCMode_PWM1;
    TIM_OCInitStructure.TIM_OCPolarity = TIM_OCPolarity_High;
    TIM_OCInitStructure.TIM_OutputState = TIM_OutputState_Enable;
    TIM_OCInitStructure.TIM_Pulse = 1550; /* 初始位置归中 */
    
    /* 配置 X 轴 (PA2 -> TIM2_CH3) */
    TIM_OC3Init(TIM2, &TIM_OCInitStructure);
    TIM_OC3PreloadConfig(TIM2, TIM_OCPreload_Enable);
    
    /* 配置 Y 轴 (PA3 -> TIM2_CH4) */
    TIM_OC4Init(TIM2, &TIM_OCInitStructure); 
    TIM_OC4PreloadConfig(TIM2, TIM_OCPreload_Enable);
    
    TIM_Cmd(TIM2, ENABLE);
}

/**
  * @brief  设置 Y 轴 (Pitch) PWM 脉宽
  * @param  Compare: PWM比较值 (500~2500)
  */
void PWM_SetCompare4(uint16_t Compare)
{
    TIM_SetCompare4(TIM2, Compare);
}

/**
  * @brief  设置 X 轴 (Yaw) PWM 脉宽
  * @param  Compare: PWM比较值 (500~2500)
  */
void PWM_SetCompare3(uint16_t Compare)
{
    TIM_SetCompare3(TIM2, Compare);
}
