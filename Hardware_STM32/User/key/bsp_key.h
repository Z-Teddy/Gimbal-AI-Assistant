/**
  ******************************************************************************
  * @file    bsp_key.h
  * @author  Z-Teddy
  * @brief   按键驱动头文件
  * @note    Reference: Based on Wildfire BSP (Modified for standardization)
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#ifndef __KEY_H
#define __KEY_H

#include "stm32f10x.h"

/* =================================================================================
 * 硬件 GPIO 定义
 * ================================================================================= */

/* KEY1 (PA0) */
#define    KEY1_GPIO_CLK     RCC_APB2Periph_GPIOA
#define    KEY1_GPIO_PORT    GPIOA             
#define    KEY1_GPIO_PIN     GPIO_Pin_0

/* KEY2 (PC13) */
#define    KEY2_GPIO_CLK     RCC_APB2Periph_GPIOC
#define    KEY2_GPIO_PORT    GPIOC         
#define    KEY2_GPIO_PIN     GPIO_Pin_13

/* =================================================================================
 * 按键状态定义
 * ================================================================================= */

/** @brief 按键按下标志宏
  * @note  当前配置：高电平有效 (按下=1, 松开=0)
  * 若电路改为低电平有效，请交换下方宏定义的值
  */
#define KEY_ON  1
#define KEY_OFF 0

/* =================================================================================
 * 函数声明
 * ================================================================================= */

/**
  * @brief  初始化按键 GPIO
  */
void Key_GPIO_Config(void);

/**
  * @brief  按键扫描函数
  * @param  GPIOx: 端口号
  * @param  GPIO_Pin: 引脚号
  * @retval KEY_ON / KEY_OFF
  */
uint8_t Key_Scan(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);

#endif /* __KEY_H */
