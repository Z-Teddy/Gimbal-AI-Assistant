/**
  ******************************************************************************
  * @file    bsp_key.c
  * @author  Z-Teddy
  * @brief   按键底层驱动配置
  * @note    Reference: Based on Wildfire BSP (Modified for standardization)
  ******************************************************************************
  */

#include "bsp_key.h"

/**
  * @brief  配置按键用到的I/O口
  * @param  无
  * @retval 无
  */
void Key_GPIO_Config(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    
    /* 开启按键端口的时钟 (GPIOA 和 GPIOC) */
    RCC_APB2PeriphClockCmd(KEY1_GPIO_CLK | KEY2_GPIO_CLK, ENABLE);
    
    /* ---------------- 配置 KEY1 (PA0) ---------------- */
    GPIO_InitStructure.GPIO_Pin = KEY1_GPIO_PIN; 
    
    /* 设置为下拉输入 (IPD) */
    /* 作用：松手时内部电阻拉地(0)，按下时接通电源(1) */
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPD; 
    GPIO_Init(KEY1_GPIO_PORT, &GPIO_InitStructure);
    
    /* ---------------- 配置 KEY2 (PC13) ---------------- */
    GPIO_InitStructure.GPIO_Pin = KEY2_GPIO_PIN; 
    
    /* 同样设置为下拉输入 (IPD)，逻辑与 KEY1 保持一致 */
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPD; 
    GPIO_Init(KEY2_GPIO_PORT, &GPIO_InitStructure); 
}

/**
  * @brief  按键扫描函数
  * @param  GPIOx: 端口号 (如 GPIOA)
  * @param  GPIO_Pin: 引脚号 (如 GPIO_Pin_0)
  * @retval KEY_ON(1): 按下, KEY_OFF(0): 没按
  */
uint8_t Key_Scan(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin)
{
    /* 检测是否有按键按下 (因为都是高电平有效，所以检测 1) */
    if(GPIO_ReadInputDataBit(GPIOx, GPIO_Pin) == 1)
    {
        /* 简单的松手检测 (阻塞式，用于简单测试) */
        /* 如果是在 FreeRTOS 任务中频繁调用，建议去掉这行 while 或改用 vTaskDelay */
        while(GPIO_ReadInputDataBit(GPIOx, GPIO_Pin) == 1); 
        
        return KEY_ON; /* 返回 1 */
    }
    else
    {
        return KEY_OFF; /* 返回 0 */
    }
}

/*********************************************END OF FILE**********************/