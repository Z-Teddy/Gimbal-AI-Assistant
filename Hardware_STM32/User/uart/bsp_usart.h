/**
  ******************************************************************************
  * @file    bsp_usart.h
  * @author  Z-Teddy
  * @brief   USART底层驱动头文件
  * @note    Reference: Based on Wildfire BSP (Modified for standardization)
  ******************************************************************************
  */

#ifndef __USART_H
#define __USART_H

#include "stm32f10x.h"
#include <stdio.h>

/** * @brief  串口硬件配置宏定义
  * @note   修改此处宏定义可切换使用的串口外设 (默认为 USART1)
  */

/* =================================================================================
 * 当前使用的串口配置 (USART1)
 * ================================================================================= */

#define  DEBUG_USARTx                   USART1
#define  DEBUG_USART_CLK                RCC_APB2Periph_USART1
#define  DEBUG_USART_APBxClkCmd         RCC_APB2PeriphClockCmd
#define  DEBUG_USART_BAUDRATE           115200

/* USART GPIO 引脚定义 */
#define  DEBUG_USART_GPIO_CLK           (RCC_APB2Periph_GPIOA)
#define  DEBUG_USART_GPIO_APBxClkCmd    RCC_APB2PeriphClockCmd
    
#define  DEBUG_USART_TX_GPIO_PORT       GPIOA   
#define  DEBUG_USART_TX_GPIO_PIN        GPIO_Pin_9
#define  DEBUG_USART_RX_GPIO_PORT       GPIOA
#define  DEBUG_USART_RX_GPIO_PIN        GPIO_Pin_10

/* USART 中断定义 */
#define  DEBUG_USART_IRQ                USART1_IRQn
#define  DEBUG_USART_IRQHandler         USART1_IRQHandler

/* =================================================================================
 * 备选串口配置参考 (如需使用其他串口，请修改上述宏定义)
 * ================================================================================= */
/* * [USART2]
 * CLK: RCC_APB1Periph_USART2 (APB1)
 * TX:  PA2
 * RX:  PA3
 * IRQ: USART2_IRQn
 *
 * [USART3]
 * CLK: RCC_APB1Periph_USART3 (APB1)
 * TX:  PB10
 * RX:  PB11
 * IRQ: USART3_IRQn
 *
 * [UART4]
 * CLK: RCC_APB1Periph_UART4 (APB1)
 * TX:  PC10
 * RX:  PC11
 * IRQ: UART4_IRQn
 *
 * [UART5]
 * CLK: RCC_APB1Periph_UART5 (APB1)
 * TX:  PC12
 * RX:  PD2
 * IRQ: UART5_IRQn
 */

/* =================================================================================
 * 函数声明
 * ================================================================================= */

/**
  * @brief  初始化 USART 配置
  */
void USART_Config(void);

/**
  * @brief  发送一个字节
  * @param  pUSARTx: USART外设 (如 USART1)
  * @param  ch: 要发送的字节
  */
void Usart_SendByte(USART_TypeDef * pUSARTx, uint8_t ch);

/**
  * @brief  发送字符串
  * @param  pUSARTx: USART外设
  * @param  str: 字符串指针
  */
void Usart_SendString(USART_TypeDef * pUSARTx, char *str);

/**
  * @brief  发送半字 (16位)
  * @param  pUSARTx: USART外设
  * @param  ch: 要发送的16位数据
  */
void Usart_SendHalfWord(USART_TypeDef * pUSARTx, uint16_t ch);

#endif /* __USART_H */
