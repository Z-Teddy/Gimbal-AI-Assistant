/**
  ******************************************************************************
  * @file    OLED.h
  * @author  Z-Teddy
  * @brief   0.96寸OLED驱动头文件
  * @note    Reference: Based on General OLED Driver (Modified for FreeRTOS)
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#ifndef __OLED_H
#define __OLED_H

/* =================================================================================
 * 初始化与基础控制
 * ================================================================================= */

/**
  * @brief  OLED初始化
  * @note   配置I2C引脚与屏幕控制器
  */
void OLED_Init(void);

/**
  * @brief  OLED清屏
  * @note   将显存全部清零
  */
void OLED_Clear(void);

/* =================================================================================
 * 字符与字符串显示
 * ================================================================================= */

/**
  * @brief  显示一个字符
  * @param  Line: 行位置 (1~4)
  * @param  Column: 列位置 (1~16)
  * @param  Char: 要显示的字符 (ASCII)
  */
void OLED_ShowChar(uint8_t Line, uint8_t Column, char Char);

/**
  * @brief  显示字符串
  * @param  Line: 行位置 (1~4)
  * @param  Column: 列位置 (1~16)
  * @param  String: 字符串指针
  */
void OLED_ShowString(uint8_t Line, uint8_t Column, char *String);

/* =================================================================================
 * 数值显示函数
 * ================================================================================= */

/**
  * @brief  显示无符号十进制数字
  * @param  Line: 行位置 (1~4)
  * @param  Column: 列位置 (1~16)
  * @param  Number: 要显示的数字 (0~4294967295)
  * @param  Length: 数字长度 (1~10)
  */
void OLED_ShowNum(uint8_t Line, uint8_t Column, uint32_t Number, uint8_t Length);

/**
  * @brief  显示有符号十进制数字
  * @param  Line: 行位置 (1~4)
  * @param  Column: 列位置 (1~16)
  * @param  Number: 要显示的数字 (-2147483648~2147483647)
  * @param  Length: 数字长度 (1~10)
  */
void OLED_ShowSignedNum(uint8_t Line, uint8_t Column, int32_t Number, uint8_t Length);

/**
  * @brief  显示十六进制数字
  * @param  Line: 行位置 (1~4)
  * @param  Column: 列位置 (1~16)
  * @param  Number: 要显示的数字
  * @param  Length: 数字长度 (1~8)
  */
void OLED_ShowHexNum(uint8_t Line, uint8_t Column, uint32_t Number, uint8_t Length);

/**
  * @brief  显示二进制数字
  * @param  Line: 行位置 (1~4)
  * @param  Column: 列位置 (1~16)
  * @param  Number: 要显示的数字
  * @param  Length: 数字长度 (1~16)
  */
void OLED_ShowBinNum(uint8_t Line, uint8_t Column, uint32_t Number, uint8_t Length);

#endif
