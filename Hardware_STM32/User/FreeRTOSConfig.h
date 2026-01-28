/**
  ******************************************************************************
  * @file    FreeRTOSConfig.h
  * @author  Z-Teddy
  * @brief   FreeRTOS 核心配置文件
  * @note    Reference: Based on Wildfire FreeRTOS Config (Modified for standardization)
  ******************************************************************************
  */

#ifndef FREERTOS_CONFIG_H
#define FREERTOS_CONFIG_H

#include "stm32f10x.h"
#include "bsp_usart.h"

/* 针对不同编译器的 stdint.h 兼容处理 */
#if defined(__ICCARM__) || defined(__CC_ARM) || defined(__GNUC__)
    #include <stdint.h>
    extern uint32_t SystemCoreClock;
#endif

/* 断言配置 */
#define vAssertCalled(char, int) printf("Error:%s,%d\r\n", char, int)
#define configASSERT(x) if ((x) == 0) vAssertCalled(__FILE__, __LINE__)

/* =================================================================================
 * 基础配置 (Basic Configuration)
 * ================================================================================= */

/** @brief 置1：使用抢占式调度器；置0：使用协作式调度器 */
#define configUSE_PREEMPTION                    1

/** @brief 置1：使能时间片调度 (默认使能) */
#define configUSE_TIME_SLICING                  1

/** @brief 优化任务选择算法 (硬件计算前导零指令 CLZ) */
/* STM32F103 (Cortex-M3) 支持 CLZ 指令，建议置 1 以提高性能 */
#define configUSE_PORT_OPTIMISED_TASK_SELECTION 1

/** @brief 低功耗 Tickless 模式 (置 1 开启，调试时建议关闭) */
#define configUSE_TICKLESS_IDLE                 0

/** @brief CPU 核心时钟频率 (Hz) */
#define configCPU_CLOCK_HZ                      (SystemCoreClock)

/** @brief RTOS 系统节拍频率 (Hz) -> 1000Hz = 1ms/tick */
#define configTICK_RATE_HZ                      ((TickType_t)1000)

/** @brief 最大任务优先级 (0 ~ 31) */
#define configMAX_PRIORITIES                    (32)

/** @brief 空闲任务栈大小 (单位: Word = 4 Bytes) */
#define configMINIMAL_STACK_SIZE                ((unsigned short)128)

/** @brief 任务名称最大长度 */
#define configMAX_TASK_NAME_LEN                 (16)

/** @brief 系统节拍计数器宽度 (0: 32位, 1: 16位) */
#define configUSE_16_BIT_TICKS                  0

/** @brief 空闲任务是否让出 CPU 给同优先级任务 */
#define configIDLE_SHOULD_YIELD                 1

/** @brief 启用队列集功能 */
#define configUSE_QUEUE_SETS                    0

/** @brief 启用任务通知功能 */
#define configUSE_TASK_NOTIFICATIONS            1

/** @brief 启用互斥信号量 */
#define configUSE_MUTEXES                       0

/** @brief 启用递归互斥信号量 */
#define configUSE_RECURSIVE_MUTEXES             0

/** @brief 启用计数信号量 */
#define configUSE_COUNTING_SEMAPHORES           0

/** @brief 信号量和队列注册表大小 (用于调试) */
#define configQUEUE_REGISTRY_SIZE               10

/** @brief 启用应用任务标签 */
#define configUSE_APPLICATION_TASK_TAG          0

/* =================================================================================
 * 内存管理 (Memory Management)
 * ================================================================================= */

/** @brief 支持动态内存申请 (heap_x.c) */
#define configSUPPORT_DYNAMIC_ALLOCATION        1

/** @brief 支持静态内存申请 */
#define configSUPPORT_STATIC_ALLOCATION         0

/** @brief 系统堆总大小 (单位: Byte) -> 36KB */
#define configTOTAL_HEAP_SIZE                   ((size_t)(36 * 1024))

/* =================================================================================
 * 钩子函数 (Hook Functions)
 * ================================================================================= */

/** @brief 空闲任务钩子 (vApplicationIdleHook) */
#define configUSE_IDLE_HOOK                     0

/** @brief 时间片钩子 (vApplicationTickHook) */
#define configUSE_TICK_HOOK                     0

/** @brief 内存申请失败钩子 (vApplicationMallocFailedHook) */
#define configUSE_MALLOC_FAILED_HOOK            1

/** @brief 栈溢出检测钩子 (vApplicationStackOverflowHook)
  * 0: 关闭, 1: 方法1, 2: 方法2 (推荐)
  */
#define configCHECK_FOR_STACK_OVERFLOW          2

/* =================================================================================
 * 运行时间与状态统计 (Run Time & State Stats)
 * ================================================================================= */

/** @brief 启用运行时间统计 */
#define configGENERATE_RUN_TIME_STATS           0

/** @brief 启用可视化跟踪调试 */
#define configUSE_TRACE_FACILITY                0

/** @brief 启用格式化统计函数 (vTaskList, vTaskGetRunTimeStats) */
#define configUSE_STATS_FORMATTING_FUNCTIONS    1

/* =================================================================================
 * 协程配置 (Co-routines)
 * ================================================================================= */

/** @brief 启用协程 */
#define configUSE_CO_ROUTINES                   0

/** @brief 协程优先级数量 */
#define configMAX_CO_ROUTINE_PRIORITIES         (2)

/* =================================================================================
 * 软件定时器 (Software Timers)
 * ================================================================================= */

/** @brief 启用软件定时器 */
#define configUSE_TIMERS                        1

/** @brief 软件定时器服务任务优先级 */
#define configTIMER_TASK_PRIORITY               (configMAX_PRIORITIES - 1)

/** @brief 软件定时器命令队列长度 */
#define configTIMER_QUEUE_LENGTH                10

/** @brief 软件定时器任务栈大小 */
#define configTIMER_TASK_STACK_DEPTH            (configMINIMAL_STACK_SIZE * 2)

/* =================================================================================
 * API 函数裁剪 (Optional Functions)
 * ================================================================================= */
#define INCLUDE_xTaskGetSchedulerState          1
#define INCLUDE_vTaskPrioritySet                1
#define INCLUDE_uxTaskPriorityGet               1
#define INCLUDE_vTaskDelete                     1
#define INCLUDE_vTaskCleanUpResources           1
#define INCLUDE_vTaskSuspend                    1
#define INCLUDE_vTaskDelayUntil                 1
#define INCLUDE_vTaskDelay                      1
#define INCLUDE_eTaskGetState                   1
#define INCLUDE_xTimerPendFunctionCall          0

/* =================================================================================
 * 中断优先级配置 (Interrupt Configuration)
 * ================================================================================= */

#ifdef __NVIC_PRIO_BITS
    #define configPRIO_BITS                     __NVIC_PRIO_BITS
#else
    #define configPRIO_BITS                     4
#endif

/** @brief 库函数使用的最低中断优先级 (15) */
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY         15

/** @brief FreeRTOS 可管理的最高中断优先级 (5)
  * 优先级高于此值的中断不受 RTOS 管控，不能调用 FreeRTOS API
  */
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY    5

/* 内核中断优先级 (移位处理) */
#define configKERNEL_INTERRUPT_PRIORITY         (configLIBRARY_LOWEST_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))

/* 系统调用中断优先级 (移位处理) */
#define configMAX_SYSCALL_INTERRUPT_PRIORITY    (configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))

/* =================================================================================
 * 中断处理函数映射 (Interrupt Handlers Mapping)
 * ================================================================================= */
#define xPortPendSVHandler                      PendSV_Handler
#define vPortSVCHandler                         SVC_Handler

/* Tracealyzer 配置 (可选) */
#if (configUSE_TRACE_FACILITY == 1)
    #include "trcRecorder.h"
    #define INCLUDE_xTaskGetCurrentTaskHandle   1
#endif

#endif /* FREERTOS_CONFIG_H */
