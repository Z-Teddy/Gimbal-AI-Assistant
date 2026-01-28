/**
  ******************************************************************************
  * @file    freertos_hooks.c
  * @author  Z-Teddy
  * @brief   FreeRTOS 钩子函数实现
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  * @note    包含栈溢出检测与内存分配失败检测，提供 LED 闪烁报警功能
  ******************************************************************************
  */

#include "stm32f10x.h"
#include "FreeRTOS.h"
#include "task.h"

/* =================================================================================
 * LED 报警配置 (可选)
 * ================================================================================= */
/** * @brief  硬件 LED 配置宏
  * @note   若需启用 LED 报警功能，请取消下方注释并根据实际硬件修改引脚定义
  */
//#define HOOK_USE_LED        1
//#define HOOK_LED_GPIO_RCC   RCC_APB2Periph_GPIOC
//#define HOOK_LED_GPIO_PORT  GPIOC
//#define HOOK_LED_PIN        GPIO_Pin_13

/* =================================================================================
 * 辅助函数
 * ================================================================================= */

/**
  * @brief  简易软件延时函数
  * @note   使用 volatile 防止编译器优化掉延时循环
  * @param  t: 延时计数
  */
static void hook_delay_loop(volatile uint32_t t)
{
    while (t--) { __NOP(); }
}

#if defined(HOOK_USE_LED) && (HOOK_USE_LED == 1)
/**
  * @brief  初始化报警 LED GPIO
  */
static void hook_led_init(void)
{
    RCC_APB2PeriphClockCmd(HOOK_LED_GPIO_RCC, ENABLE);

    GPIO_InitTypeDef gpio;
    gpio.GPIO_Pin = HOOK_LED_PIN;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    gpio.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_Init(HOOK_LED_GPIO_PORT, &gpio);

    GPIO_SetBits(HOOK_LED_GPIO_PORT, HOOK_LED_PIN);
}

/**
  * @brief  翻转报警 LED 状态
  */
static void hook_led_toggle(void)
{
    if (GPIO_ReadOutputDataBit(HOOK_LED_GPIO_PORT, HOOK_LED_PIN))
        GPIO_ResetBits(HOOK_LED_GPIO_PORT, HOOK_LED_PIN);
    else
        GPIO_SetBits(HOOK_LED_GPIO_PORT, HOOK_LED_PIN);
}
#endif

/* =================================================================================
 * FreeRTOS 钩子函数实现
 * ================================================================================= */

/**
  * @brief  内存分配失败钩子函数 (Malloc Failed Hook)
  * @note   当 heap 不足导致 pvPortMalloc 分配失败时调用此函数
  * @note   表现为：LED 慢闪 (周期约 1.6s)
  */
void vApplicationMallocFailedHook(void)
{
    taskDISABLE_INTERRUPTS();

#if defined(HOOK_USE_LED) && (HOOK_USE_LED == 1)
    hook_led_init();
#endif

    /* 进入死循环报警 */
    for (;;)
    {
#if defined(HOOK_USE_LED) && (HOOK_USE_LED == 1)
        hook_led_toggle();
#endif
        /* 慢闪表示内存分配失败 */
        hook_delay_loop(800000);
    }
}

/**
  * @brief  任务栈溢出钩子函数 (Stack Overflow Hook)
  * @note   需在 FreeRTOSConfig.h 中定义 configCHECK_FOR_STACK_OVERFLOW > 0
  * @note   表现为：LED 快闪 (周期约 0.4s)
  * @param  xTask: 发生溢出的任务句柄
  * @param  pcTaskName: 发生溢出的任务名称
  */
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    (void)xTask;
    (void)pcTaskName;

    taskDISABLE_INTERRUPTS();

#if defined(HOOK_USE_LED) && (HOOK_USE_LED == 1)
    hook_led_init();
#endif

    /* 进入死循环报警 */
    for (;;)
    {
#if defined(HOOK_USE_LED) && (HOOK_USE_LED == 1)
        hook_led_toggle();
#endif
        /* 快闪表示栈溢出 */
        hook_delay_loop(200000);
    }
}

/**
  * @brief  空闲任务钩子函数 (Idle Hook)
  * @note   需在 FreeRTOSConfig.h 中定义 configUSE_IDLE_HOOK == 1
  * @note   注意：不要在此函数中执行阻塞或耗时操作
  */
//void vApplicationIdleHook(void)
//{
//    /* 示例：执行 WFI 指令进入低功耗模式 */
//    // __WFI();
//}
