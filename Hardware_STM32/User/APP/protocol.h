/**
  ******************************************************************************
  * @file    protocol.h
  * @author  Z-Teddy
  * @brief   Õ®–≈–≠“È∂®“ÂÕ∑Œƒº˛ (÷∏¡Ó°¢ƒ£ Ω”Î ˝æ›Ω·ππ)
  * @repo    https://github.com/Z-Teddy/Gimbal-AI-Assistant
  ******************************************************************************
  */

#ifndef __PROTOCOL_H
#define __PROTOCOL_H

#include "stm32f10x.h"
#include "FreeRTOS.h"
#include "queue.h"

/* =================================================================================
 * –≠“È÷∏¡Ó≥£¡ø (Command IDs)
 * ================================================================================= */
#define PROT_CMD_HEARTBEAT      0x01    /*!< Command: heartbeat */
#define PROT_CMD_TRACK_FACE     0x02    /*!< ∏∏‰: π˛»À◊∑◊Ÿ ˝æ›∞¸ */
#define PROT_CMD_SET_ANGLE      0x03    /*!< ∏∏‰: …Ë÷√æ¯∂‘Ω«∂» (”Ô“Ù«øøÿ) */
#define PROT_CMD_SET_EXPRESSION 0x04    /*!< ∏∏‰: …Ë÷√±Ì«Èœ‘ æ */
#define PROT_CMD_NO_TARGET      0x05    /*!< Command: no target */
#define PROT_CMD_SET_MODE       0x06    /*!< Command: set mode (reserved) */

/* =================================================================================
 * œµÕ≥ ˝æ›¿‡–Õ∂®“Â
 * ================================================================================= */

/** * @brief œµÕ≥‘À––ƒ£ Ω√∂æŸ
  */
typedef enum {
    MODE_AUTO_TRACKING = 0, /*!< ◊‘∂Øƒ£ Ω£∫ ”æı PID ±’ª∑∏˙◊Ÿ */
    MODE_MANUAL_CMD    = 1  /*!<  ÷∂Øƒ£ Ω£∫œÏ”¶”Ô“Ù/Õ‚≤ø÷∏¡Ó«øøÿ */
} SystemMode_t;

/** * @brief ‘∆Ã®øÿ÷∆÷∏¡ÓΩ·ππÃÂ (œ˚œ¢∂”¡–‘ÿ∫…)
  * @note  ’‚ «“ª∏ˆÕ®”√‘ÿ∫…Ω·ππ£¨∏˘æ› cmd_id ∂¡»°∂‘”¶µƒ◊÷∂Œ
  */
typedef struct {
    uint8_t  cmd_id;    /*!< ÷∏¡Ó ID (æˆ∂®∞¸¿‡–Õ) */
    
    /* ◊∑◊Ÿƒ£ Ω ˝æ› (PROT_CMD_TRACK_FACE) */
    int16_t  x;         /*!< ƒø±Í X ◊¯±Í */
    int16_t  y;         /*!< ƒø±Í Y ◊¯±Í */
    
    /* Ω«∂»øÿ÷∆ƒ£ Ω ˝æ› (PROT_CMD_SET_ANGLE) */
    float    f_yaw;     /*!< ƒø±Í∆´∫ΩΩ« (Yaw) */
    float    f_pitch;   /*!< ƒø±Í∏©—ˆΩ« (Pitch) */
    
    /* ±Ì«Èøÿ÷∆ƒ£ Ω ˝æ› (PROT_CMD_SET_EXPRESSION) */
    uint8_t  face_id;   /*!< ±Ì«È ID À˜“˝ */
} GimbalCmd_t;

/* =================================================================================
 * µº≥ˆ±‰¡ø”Î∫Ø ˝Ω”ø⁄
 * ================================================================================= */

/* »´æ÷◊¥Ã¨±‰¡ø */
extern SystemMode_t g_SystemMode;   /*!< µ±«∞œµÕ≥π§◊˜ƒ£ Ω */
extern QueueHandle_t xCmdQueue;     /*!< ÷∏¡Óœ˚œ¢∂”¡–æ‰±˙ */
extern volatile TickType_t g_last_link_tick;      /*!< Last valid link activity tick */
extern volatile uint8_t g_target_available;       /*!< 1 when target packets are active */
extern volatile uint8_t g_last_no_target_reason;  /*!< Last no-target reason code */

/**
  * @brief  –≠“È’ª≥ı ºªØ
  * @note   ¥¥Ω®∂”¡–”Î∂® ±∆˜◊ ‘¥
  */
void Protocol_Init(void);

/**
  * @brief  ¥Æø⁄◊÷Ω⁄¡˜Ω‚Œˆ◊¥Ã¨ª˙
  * @note   –Ë‘⁄¥Æø⁄Ω” ’÷–∂œ (ISR) ÷–µ˜”√
  * @param  byte: Ω” ’µΩµƒµ•◊÷Ω⁄ ˝æ›
  */
void Protocol_ParseByte_ISR(uint8_t byte);

#endif