/*
 * Shared audio (I2S mic/speaker) + UART binary protocol + MCP stream hooks.
 */

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

void audio_mcp_init(void);
void audio_mcp_uart_proto_task(void *pv);

/** MCP: start mic PCM into internal byte ringbuffer; enables GET /mcp/stream/mic. */
esp_err_t audio_mcp_mcp_subscribe(uint32_t sample_rate_hz, uint8_t channels);
void audio_mcp_mcp_unsubscribe(void);
bool audio_mcp_mcp_subscribed(void);

/** Decode base64 PCM (s16le) and play on speaker. */
esp_err_t audio_mcp_speaker_play_pcm_b64(const char *pcm_base64, uint32_t sample_rate_hz,
                                         uint8_t channels);

/** For mcp_http.c: mic stream GET (ringbuffer + metadata). */
bool audio_mcp_mcp_stream_http_ready(void);
bool audio_mcp_mic_task_running(void);
uint32_t audio_mcp_get_mic_sample_rate(void);
uint8_t audio_mcp_get_mic_channels(void);
void *audio_mcp_mcp_ringbuf_receive(size_t *item_size, uint32_t wait_ms);
void audio_mcp_mcp_ringbuf_return(void *item);

#ifdef __cplusplus
}
#endif
