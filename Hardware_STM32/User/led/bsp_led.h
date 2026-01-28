/**
  ******************************************************************************
  * @file    bsp_led.h
  * @author  Z-Teddy
  * @brief   LED 底层驱动头文件
  * @note    Reference: Based on Wildfire BSP (Modified for standardization)
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#ifndef __LED_H
#define __LED_H

#include "stm32f10x.h"

/* =================================================================================
 * 硬件 GPIO 定义
 * ================================================================================= */

/* R - 红色 LED */
#define LED1_GPIO_PORT          GPIOB                   /*!< GPIO 端口 */
#define LED1_GPIO_CLK           RCC_APB2Periph_GPIOB    /*!< GPIO 端口时钟 */
#define LED1_GPIO_PIN           GPIO_Pin_5              /*!< 连接 LED1 的引脚 */

/* G - 绿色 LED */
#define LED2_GPIO_PORT          GPIOB                   /*!< GPIO 端口 */
#define LED2_GPIO_CLK           RCC_APB2Periph_GPIOB    /*!< GPIO 端口时钟 */
#define LED2_GPIO_PIN           GPIO_Pin_0              /*!< 连接 LED2 的引脚 */

/* B - 蓝色 LED */
#define LED3_GPIO_PORT          GPIOB                   /*!< GPIO 端口 */
#define LED3_GPIO_CLK           RCC_APB2Periph_GPIOB    /*!< GPIO 端口时钟 */
#define LED3_GPIO_PIN           GPIO_Pin_1              /*!< 连接 LED3 的引脚 */

/* =================================================================================
 * 逻辑状态定义
 * ================================================================================= */

/** * @brief  LED 开关状态宏定义
  * @note   1 - OFF (高电平灭), 0 - ON (低电平亮)
  */
#define ON  0
#define OFF 1

/* =================================================================================
 * 控制宏 (标准库版本)
 * ================================================================================= */

#define LED1(a) if (a)  \
        GPIO_SetBits(LED1_GPIO_PORT, LED1_GPIO_PIN);    \
    else                \
        GPIO_ResetBits(LED1_GPIO_PORT, LED1_GPIO_PIN)

#define LED2(a) if (a)  \
        GPIO_SetBits(LED2_GPIO_PORT, LED2_GPIO_PIN);    \
    else                \
        GPIO_ResetBits(LED2_GPIO_PORT, LED2_GPIO_PIN)

#define LED3(a) if (a)  \
        GPIO_SetBits(LED3_GPIO_PORT, LED3_GPIO_PIN);    \
    else                \
        GPIO_ResetBits(LED3_GPIO_PORT, LED3_GPIO_PIN)

/* =================================================================================
 * 控制宏 (寄存器版本 - 高效)
 * ================================================================================= */

#define digitalHi(p, i)       {p->BSRR = i;}    /*!< 输出高电平 */
#define digitalLo(p, i)       {p->BRR  = i;}    /*!< 输出低电平 */
#define digitalToggle(p, i)   {p->ODR ^= i;}    /*!< 输出反转状态 */

/* 定义控制 IO 的宏 */
#define LED1_TOGGLE     digitalToggle(LED1_GPIO_PORT, LED1_GPIO_PIN)
#define LED1_OFF        digitalHi(LED1_GPIO_PORT, LED1_GPIO_PIN)
#define LED1_ON         digitalLo(LED1_GPIO_PORT, LED1_GPIO_PIN)

#define LED2_TOGGLE     digitalToggle(LED2_GPIO_PORT, LED2_GPIO_PIN)
#define LED2_OFF        digitalHi(LED2_GPIO_PORT, LED2_GPIO_PIN)
#define LED2_ON         digitalLo(LED2_GPIO_PORT, LED2_GPIO_PIN)

#define LED3_TOGGLE     digitalToggle(LED3_GPIO_PORT, LED3_GPIO_PIN)
#define LED3_OFF        digitalHi(LED3_GPIO_PORT, LED3_GPIO_PIN)
#define LED3_ON         digitalLo(LED3_GPIO_PORT, LED3_GPIO_PIN)

/* =================================================================================
 * 颜色混合宏 (基本混色)
 * ================================================================================= */

/* 红 */
#define LED_RED \
    LED1_ON;    \
    LED2_OFF    \
    LED3_OFF

/* 绿 */
#define LED_GREEN \
    LED1_OFF;     \
    LED2_ON       \
    LED3_OFF

/* 蓝 */
#define LED_BLUE \
    LED1_OFF;    \
    LED2_OFF     \
    LED3_ON

/* 黄 (红+绿) */
#define LED_YELLOW \
    LED1_ON;       \
    LED2_ON        \
    LED3_OFF

/* 紫 (红+蓝) */
#define LED_PURPLE \
    LED1_ON;       \
    LED2_OFF       \
    LED3_ON

/* 青 (绿+蓝) */
#define LED_CYAN \
    LED1_OFF;    \
    LED2_ON      \
    LED3_ON

/* 白 (红+绿+蓝) */
#define LED_WHITE \
    LED1_ON;      \
    LED2_ON       \
    LED3_ON

/* 黑 (全部关闭) */
#define LED_RGBOFF \
    LED1_OFF;      \
    LED2_OFF       \
    LED3_OFF

/* =================================================================================
 * 函数声明
 * ================================================================================= */

/**
  * @brief  初始化控制 LED 的 IO
  */
void LED_GPIO_Config(void);

#endif /* __LED_H */
