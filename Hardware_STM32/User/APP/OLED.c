/**
  ******************************************************************************
  * @file    OLED.c
  * @author  Z-Teddy
  * @brief   0.96寸OLED I2C驱动 (适配 FreeRTOS)
  * @note    Reference: Based on General OLED Driver (Modified for FreeRTOS)
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#include "stm32f10x.h"
#include "OLED_Font.h"
#include "FreeRTOS.h"
#include "task.h"

#define OLED_I2C_ADDR 0x78

/* =================================================================================
 * 辅助宏与延时函数
 * ================================================================================= */

/**
  * @brief  I2C软件延时 (微秒级)
  */
static void OLED_I2C_Delay(void)
{
    for (volatile int i = 0; i < 50; i++) { __NOP(); }
}

/* 【万能补丁】把 Delay_ms 偷梁换柱变成 FreeRTOS 的非阻塞延时 */
#define Delay_ms(x) vTaskDelay(pdMS_TO_TICKS(x))

/* 引脚控制宏 */
#define OLED_W_SCL(x)       GPIO_WriteBit(GPIOB, GPIO_Pin_8, (BitAction)(x))
#define OLED_W_SDA(x)       GPIO_WriteBit(GPIOB, GPIO_Pin_9, (BitAction)(x))

/* =================================================================================
 * 底层 I2C 驱动
 * ================================================================================= */

/**
  * @brief  I2C引脚初始化
  * @note   PB8(SCL), PB9(SDA) - 开漏输出模式
  */
void OLED_I2C_Init(void)
{
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
    
    GPIO_InitTypeDef GPIO_InitStructure;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_OD;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_8 | GPIO_Pin_9;
    GPIO_Init(GPIOB, &GPIO_InitStructure);
    
    OLED_W_SCL(1);
    OLED_W_SDA(1);
}

/**
  * @brief  I2C起始信号
  */
void OLED_I2C_Start(void)
{
    OLED_W_SDA(1); OLED_I2C_Delay();
    OLED_W_SCL(1); OLED_I2C_Delay();
    OLED_W_SDA(0); OLED_I2C_Delay();
    OLED_W_SCL(0); OLED_I2C_Delay();
}

/**
  * @brief  I2C停止信号
  */
void OLED_I2C_Stop(void)
{
    OLED_W_SDA(0); OLED_I2C_Delay();
    OLED_W_SCL(1); OLED_I2C_Delay();
    OLED_W_SDA(1); OLED_I2C_Delay();
}

/**
  * @brief  I2C发送一个字节
  * @param  Byte: 要发送的一个字节
  */
void OLED_I2C_SendByte(uint8_t Byte)
{
    for (uint8_t i = 0; i < 8; i++)
    {
        OLED_W_SDA((Byte & (0x80 >> i)) ? 1 : 0);
        OLED_I2C_Delay();

        OLED_W_SCL(1); OLED_I2C_Delay();
        OLED_W_SCL(0); OLED_I2C_Delay();
    }

    /* ACK 时钟（忽略读取ACK位，但必须产生时钟脉冲） */
    OLED_W_SCL(1); OLED_I2C_Delay();
    OLED_W_SCL(0); OLED_I2C_Delay();
}

/**
  * @brief  OLED写命令
  * @param  Command: 要写入的命令
  */
void OLED_WriteCommand(uint8_t Command)
{
    OLED_I2C_Start();
    OLED_I2C_SendByte(OLED_I2C_ADDR);       /* 从机地址 */
    OLED_I2C_SendByte(0x00);                /* 写命令控制字 */
    OLED_I2C_SendByte(Command); 
    OLED_I2C_Stop();
}

/**
  * @brief  OLED写数据
  * @param  Data: 要写入的数据
  */
void OLED_WriteData(uint8_t Data)
{
    OLED_I2C_Start();
    OLED_I2C_SendByte(OLED_I2C_ADDR);       /* 从机地址 */
    OLED_I2C_SendByte(0x40);                /* 写数据控制字 */
    OLED_I2C_SendByte(Data);
    OLED_I2C_Stop();
}

/* =================================================================================
 * OLED 应用层函数
 * ================================================================================= */

/**
  * @brief  OLED设置光标位置
  * @param  Y: 页地址 (0~7)
  * @param  X: 列地址 (0~127)
  */
void OLED_SetCursor(uint8_t Y, uint8_t X)
{
    OLED_WriteCommand(0xB0 | Y);                    /* 设置Y位置 */
    OLED_WriteCommand(0x10 | ((X & 0xF0) >> 4));    /* 设置X位置高4位 */
    OLED_WriteCommand(0x00 | (X & 0x0F));           /* 设置X位置低4位 */
}

/**
  * @brief  OLED清屏
  */
void OLED_Clear(void)
{  
    uint8_t i, j;
    for (j = 0; j < 8; j++)
    {
        OLED_SetCursor(j, 0);
        for(i = 0; i < 128; i++)
        {
            OLED_WriteData(0x00);
        }
    }
}

/**
  * @brief  OLED显示一个字符
  * @param  Line: 行位置 (1~4)
  * @param  Column: 列位置 (1~16)
  * @param  Char: 要显示的字符 (ASCII)
  */
void OLED_ShowChar(uint8_t Line, uint8_t Column, char Char)
{       
    uint8_t i;
    /* 设置光标位置在上半部分 */
    OLED_SetCursor((Line - 1) * 2, (Column - 1) * 8);       
    for (i = 0; i < 8; i++)
    {
        /* 显示上半部分内容 */
        OLED_WriteData(OLED_F8x16[Char - ' '][i]);          
    }
    
    /* 设置光标位置在下半部分 */
    OLED_SetCursor((Line - 1) * 2 + 1, (Column - 1) * 8);   
    for (i = 0; i < 8; i++)
    {
        /* 显示下半部分内容 */
        OLED_WriteData(OLED_F8x16[Char - ' '][i + 8]);      
    }
}

/**
  * @brief  OLED显示字符串
  * @param  Line: 起始行位置 (1~4)
  * @param  Column: 起始列位置 (1~16)
  * @param  String: 要显示的字符串
  */
void OLED_ShowString(uint8_t Line, uint8_t Column, char *String)
{
    uint8_t i;
    for (i = 0; String[i] != '\0'; i++)
    {
        OLED_ShowChar(Line, Column + i, String[i]);
    }
}

/**
  * @brief  OLED次方函数 (辅助内部使用)
  */
uint32_t OLED_Pow(uint32_t X, uint32_t Y)
{
    uint32_t Result = 1;
    while (Y--)
    {
        Result *= X;
    }
    return Result;
}

/**
  * @brief  OLED显示数字（十进制，正数）
  * @param  Line: 起始行位置 (1~4)
  * @param  Column: 起始列位置 (1~16)
  * @param  Number: 要显示的数字 (0~4294967295)
  * @param  Length: 数字长度 (1~10)
  */
void OLED_ShowNum(uint8_t Line, uint8_t Column, uint32_t Number, uint8_t Length)
{
    uint8_t i;
    for (i = 0; i < Length; i++)                            
    {
        OLED_ShowChar(Line, Column + i, Number / OLED_Pow(10, Length - i - 1) % 10 + '0');
    }
}

/**
  * @brief  OLED显示数字（十进制，带符号数）
  * @param  Line: 起始行位置 (1~4)
  * @param  Column: 起始列位置 (1~16)
  * @param  Number: 要显示的数字 (-2147483648~2147483647)
  * @param  Length: 数字长度 (1~10)
  */
void OLED_ShowSignedNum(uint8_t Line, uint8_t Column, int32_t Number, uint8_t Length)
{
    uint8_t i;
    uint32_t Number1;
    if (Number >= 0)
    {
        OLED_ShowChar(Line, Column, '+');
        Number1 = Number;
    }
    else
    {
        OLED_ShowChar(Line, Column, '-');
        Number1 = -Number;
    }
    for (i = 0; i < Length; i++)                            
    {
        OLED_ShowChar(Line, Column + i + 1, Number1 / OLED_Pow(10, Length - i - 1) % 10 + '0');
    }
}

/**
  * @brief  OLED显示数字（十六进制，正数）
  * @param  Line: 起始行位置 (1~4)
  * @param  Column: 起始列位置 (1~16)
  * @param  Number: 要显示的数字 (0~0xFFFFFFFF)
  * @param  Length: 数字长度 (1~8)
  */
void OLED_ShowHexNum(uint8_t Line, uint8_t Column, uint32_t Number, uint8_t Length)
{
    uint8_t i, SingleNumber;
    for (i = 0; i < Length; i++)                            
    {
        SingleNumber = Number / OLED_Pow(16, Length - i - 1) % 16;
        if (SingleNumber < 10)
        {
            OLED_ShowChar(Line, Column + i, SingleNumber + '0');
        }
        else
        {
            OLED_ShowChar(Line, Column + i, SingleNumber - 10 + 'A');
        }
    }
}

/**
  * @brief  OLED显示数字（二进制，正数）
  * @param  Line: 起始行位置 (1~4)
  * @param  Column: 起始列位置 (1~16)
  * @param  Number: 要显示的数字
  * @param  Length: 数字长度 (1~16)
  */
void OLED_ShowBinNum(uint8_t Line, uint8_t Column, uint32_t Number, uint8_t Length)
{
    uint8_t i;
    for (i = 0; i < Length; i++)                            
    {
        OLED_ShowChar(Line, Column + i, Number / OLED_Pow(2, Length - i - 1) % 2 + '0');
    }
}

/**
  * @brief  OLED初始化
  */
void OLED_Init(void)
{
    uint32_t i, j;
    
    /* 延时等待上电稳定 */
    vTaskDelay(pdMS_TO_TICKS(200));
    
    OLED_I2C_Init();        /* 端口初始化 */
    
    OLED_WriteCommand(0xAE);    /* 关闭显示 */
    
    OLED_WriteCommand(0xD5);    /* 设置显示时钟分频比/振荡器频率 */
    OLED_WriteCommand(0x80);
    
    OLED_WriteCommand(0xA8);    /* 设置多路复用率 */
    OLED_WriteCommand(0x3F);
    
    OLED_WriteCommand(0xD3);    /* 设置显示偏移 */
    OLED_WriteCommand(0x00);
    
    OLED_WriteCommand(0x40);    /* 设置显示开始行 */
    
    OLED_WriteCommand(0xA1);    /* 设置左右方向，0xA1正常 0xA0左右反置 */
    
    OLED_WriteCommand(0xC8);    /* 设置上下方向，0xC8正常 0xC0上下反置 */

    OLED_WriteCommand(0xDA);    /* 设置COM引脚硬件配置 */
    OLED_WriteCommand(0x12);
    
    OLED_WriteCommand(0x81);    /* 设置对比度控制 */
    OLED_WriteCommand(0xCF);

    OLED_WriteCommand(0xD9);    /* 设置预充电周期 */
    OLED_WriteCommand(0xF1);

    OLED_WriteCommand(0xDB);    /* 设置VCOMH取消选择级别 */
    OLED_WriteCommand(0x30);

    OLED_WriteCommand(0xA4);    /* 设置整个显示打开/关闭 */

    OLED_WriteCommand(0xA6);    /* 设置正常/倒转显示 */

    OLED_WriteCommand(0x8D);    /* 设置充电泵 */
    OLED_WriteCommand(0x14);

    OLED_WriteCommand(0xAF);    /* 开启显示 */
        
    OLED_Clear();               /* OLED清屏 */
}
