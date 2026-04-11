/*
 * ESP32-S3 UART binary audio protocol + MCP mic ringbuffer stream
 * (ESP-IDF 5.x).
 *
 * Host -> device frame: 0xA5 0x5A | CMD (u8) | LEN (u16 LE) | PAYLOAD (LEN) |
 * CRC8 CRC8: Dallas/Maxim, poly 0x31, init 0, over
 * [CMD][LEN_LO][LEN_HI][PAYLOAD...]
 *
 * CMD 0x01 START_MIC: payload = sample_rate_hz (u32 LE), bits (u16 LE),
 * channels (u16 LE) CMD 0x02 STOP_MIC CMD 0x10 PLAY_PCM: payload = pcm_len (u32
 * LE) + pcm bytes (max ~512 stereo s16le frames) CMD 0x11 STOP_PLAY
 *
 * Device -> host (mic PCM): 0xB5 0x5B | 0x01 | pcm_total_len (u32 LE) | PCM
 */

#include "audio_mcp.h"

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/i2s_std.h"
#include "driver/uart.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/ringbuf.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "mbedtls/base64.h"
#include "sdkconfig.h"

static const char *TAG = "audio_mcp";

static void uart_init(void);

#define UART_PORT UART_NUM_0
#define UART_BUF_SZ (8192)
#define UART_QUEUE_SIZE 20

#define SYNC0 0xA5
#define SYNC1 0x5A

#define CMD_START_MIC 0x01
#define CMD_STOP_MIC 0x02
#define CMD_PLAY_PCM 0x10
#define CMD_STOP_PLAY 0x11

#define STREAM_SYNC0 0xB5
#define STREAM_SYNC1 0x5B
#define STREAM_SUB_MIC 0x01

#define MAX_PAYLOAD 4096
#define MAX_PLAY_PCM_BYTES 2048
#define MIC_READ_SAMPLES 512

#define MCP_RINGBUF_BYTES (32 * 1024)

#if CONFIG_AUDIO_I2S_MIC_PORT == 0
#define MIC_I2S_NUM I2S_NUM_0
#else
#define MIC_I2S_NUM I2S_NUM_1
#endif

#if CONFIG_AUDIO_I2S_SPK_PORT == 0
#define SPK_I2S_NUM I2S_NUM_0
#else
#define SPK_I2S_NUM I2S_NUM_1
#endif

#if MIC_I2S_NUM == SPK_I2S_NUM
#error                                                                         \
    "CONFIG_AUDIO_I2S_MIC_PORT and CONFIG_AUDIO_I2S_SPK_PORT must differ for duplex."
#endif

static i2s_chan_handle_t s_rx = NULL;
static i2s_chan_handle_t s_tx = NULL;
static bool s_mic_i2s_ok;
static bool s_spk_i2s_ok;
static SemaphoreHandle_t s_uart_tx_mutex;
static TaskHandle_t s_mic_task = NULL;
static volatile bool s_mic_run;
static uint32_t s_mic_rate = 16000;
static uint8_t s_mic_ch = 1;

static bool s_stream_uart;
static bool s_stream_mcp;
static RingbufHandle_t s_mcp_ringbuf;

static uint8_t crc8_dallas(const uint8_t *data, size_t len) {
  uint8_t crc = 0;
  for (size_t i = 0; i < len; i++) {
    crc ^= data[i];
    for (int b = 0; b < 8; b++) {
      crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x07) : (uint8_t)(crc << 1);
    }
  }
  return crc;
}

static esp_err_t uart_tx_locked(const void *data, size_t len) {
  if (s_uart_tx_mutex == NULL) {
    return ESP_ERR_INVALID_STATE;
  }
  xSemaphoreTake(s_uart_tx_mutex, portMAX_DELAY);
  int w = uart_write_bytes(UART_PORT, data, len);
  xSemaphoreGive(s_uart_tx_mutex);
  return (w == (int)len) ? ESP_OK : ESP_FAIL;
}

static void i2s_mic_teardown(void) {
  if (s_rx) {
    i2s_channel_disable(s_rx);
    i2s_del_channel(s_rx);
    s_rx = NULL;
  }
}

static void i2s_spk_teardown(void) {
  if (s_tx) {
    i2s_channel_disable(s_tx);
    i2s_del_channel(s_tx);
    s_tx = NULL;
  }
}

static gpio_num_t cfg_gpio(int cfg_val) {
  if (cfg_val < 0) {
    return GPIO_NUM_NC;
  }
  return (gpio_num_t)cfg_val;
}

static esp_err_t i2s_mic_setup(uint32_t sample_rate_hz, uint8_t channels) {
  i2s_mic_teardown();

  i2s_chan_config_t chan_cfg =
      I2S_CHANNEL_DEFAULT_CONFIG(MIC_I2S_NUM, I2S_ROLE_MASTER);
  chan_cfg.dma_desc_num = 6;
  chan_cfg.dma_frame_num = 256;

  esp_err_t err = i2s_new_channel(&chan_cfg, NULL, &s_rx);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "i2s_new_channel mic failed: %s", esp_err_to_name(err));
    return err;
  }

  i2s_std_slot_mask_t slot_mask = I2S_STD_SLOT_LEFT;
  i2s_slot_mode_t slot_mode =
      (channels >= 2) ? I2S_SLOT_MODE_STEREO : I2S_SLOT_MODE_MONO;

  i2s_std_config_t std_cfg = {
      .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(sample_rate_hz),
      .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,
                                                      slot_mode),
      .gpio_cfg =
          {
              .mclk = I2S_GPIO_UNUSED,
              .bclk = cfg_gpio(CONFIG_AUDIO_I2S_MIC_BCLK_GPIO),
              .ws = cfg_gpio(CONFIG_AUDIO_I2S_MIC_WS_GPIO),
              .dout = I2S_GPIO_UNUSED,
              .din = cfg_gpio(CONFIG_AUDIO_I2S_MIC_DIN_GPIO),
              .invert_flags =
                  {
                      .mclk_inv = false,
                      .bclk_inv = false,
                      .ws_inv = false,
                  },
          },
  };
  if (slot_mode == I2S_SLOT_MODE_MONO) {
    std_cfg.slot_cfg.slot_mask = slot_mask;
  }

  err = i2s_channel_init_std_mode(s_rx, &std_cfg);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "i2s_channel_init_std_mode mic failed: %s",
             esp_err_to_name(err));
    i2s_mic_teardown();
    return err;
  }
  err = i2s_channel_enable(s_rx);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "i2s_channel_enable mic failed: %s", esp_err_to_name(err));
    i2s_mic_teardown();
    return err;
  }
  return ESP_OK;
}

static esp_err_t i2s_spk_setup(uint32_t sample_rate_hz, uint8_t channels) {
  i2s_spk_teardown();

  i2s_chan_config_t chan_cfg =
      I2S_CHANNEL_DEFAULT_CONFIG(SPK_I2S_NUM, I2S_ROLE_MASTER);
  chan_cfg.dma_desc_num = 6;
  chan_cfg.dma_frame_num = 256;

  esp_err_t err = i2s_new_channel(&chan_cfg, &s_tx, NULL);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "i2s_new_channel spk failed: %s", esp_err_to_name(err));
    return err;
  }

  i2s_std_slot_mask_t slot_mask = I2S_STD_SLOT_LEFT;
  i2s_slot_mode_t slot_mode =
      (channels >= 2) ? I2S_SLOT_MODE_STEREO : I2S_SLOT_MODE_MONO;

  i2s_std_config_t std_cfg = {
      .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(sample_rate_hz),
      .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,
                                                      slot_mode),
      .gpio_cfg =
          {
              .mclk = I2S_GPIO_UNUSED,
              .bclk = cfg_gpio(CONFIG_AUDIO_I2S_SPK_BCLK_GPIO),
              .ws = cfg_gpio(CONFIG_AUDIO_I2S_SPK_WS_GPIO),
              .dout = cfg_gpio(CONFIG_AUDIO_I2S_SPK_DOUT_GPIO),
              .din = I2S_GPIO_UNUSED,
              .invert_flags =
                  {
                      .mclk_inv = false,
                      .bclk_inv = false,
                      .ws_inv = false,
                  },
          },
  };
  if (slot_mode == I2S_SLOT_MODE_MONO) {
    std_cfg.slot_cfg.slot_mask = slot_mask;
  }

  err = i2s_channel_init_std_mode(s_tx, &std_cfg);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "i2s_channel_init_std_mode spk failed: %s",
             esp_err_to_name(err));
    i2s_spk_teardown();
    return err;
  }
  err = i2s_channel_enable(s_tx);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "i2s_channel_enable spk failed: %s", esp_err_to_name(err));
    i2s_spk_teardown();
    return err;
  }
  return ESP_OK;
}

static void try_init_i2s_stubs(void) {
  s_mic_i2s_ok = false;
  s_spk_i2s_ok = false;

  esp_err_t m = i2s_mic_setup(16000, 1);
  if (m == ESP_OK) {
    s_mic_i2s_ok = true;
    ESP_LOGI(TAG, "I2S microphone initialized (16 kHz mono probe).");
  } else {
    ESP_LOGE(TAG, "I2S microphone init failed; mic streaming disabled (stub).");
  }

  esp_err_t p = i2s_spk_setup(16000, 1);
  if (p == ESP_OK) {
    s_spk_i2s_ok = true;
    ESP_LOGI(TAG, "I2S speaker initialized (16 kHz mono probe).");
  } else {
    ESP_LOGE(TAG, "I2S speaker init failed; playback disabled (stub).");
  }

  if (s_mic_i2s_ok) {
    i2s_mic_teardown();
  }
  if (s_spk_i2s_ok) {
    i2s_spk_teardown();
  }
}

static void mic_stop_hw(void) {
  s_mic_run = false;
  vTaskDelay(pdMS_TO_TICKS(80));
  s_mic_task = NULL;
  i2s_mic_teardown();
  s_mic_i2s_ok = false;
  if (s_mcp_ringbuf) {
    vRingbufferDelete(s_mcp_ringbuf);
    s_mcp_ringbuf = NULL;
  }
}

static void mic_task(void *arg) {
  const size_t bytes_per_frame = 2 * s_mic_ch;
  const size_t want_bytes = MIC_READ_SAMPLES * bytes_per_frame;
  uint8_t *buf =
      heap_caps_malloc(want_bytes, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
  if (!buf) {
    buf = malloc(want_bytes);
  }
  if (!buf) {
    ESP_LOGE(TAG, "mic_task: buffer alloc failed");
    s_mic_run = false;
    vTaskDelete(NULL);
    return;
  }

  while (s_mic_run && (s_stream_uart || s_stream_mcp)) {
    if (!s_mic_i2s_ok || s_rx == NULL) {
      vTaskDelay(pdMS_TO_TICKS(50));
      continue;
    }
    size_t br = 0;
    esp_err_t r =
        i2s_channel_read(s_rx, buf, want_bytes, &br, pdMS_TO_TICKS(500));
    if (r != ESP_OK || br == 0) {
      continue;
    }
    if (s_stream_uart) {
      uint8_t hdr[8] = {
          STREAM_SYNC0, STREAM_SYNC1, STREAM_SUB_MIC, 0, 0, 0, 0, 0};
      uint32_t le = (uint32_t)br;
      memcpy(&hdr[3], &le, 4);
      uart_tx_locked(hdr, sizeof(hdr));
      uart_tx_locked(buf, br);
    }
    if (s_stream_mcp && s_mcp_ringbuf) {
      if (xRingbufferGetCurFreeSize(s_mcp_ringbuf) < br + 64) {
        size_t item_size = 0;
        void *old = xRingbufferReceive(s_mcp_ringbuf, &item_size, 0);
        if (old) {
          vRingbufferReturnItem(s_mcp_ringbuf, old);
        }
      }
      (void)xRingbufferSend(s_mcp_ringbuf, buf, br, pdMS_TO_TICKS(10));
    }
  }
  free(buf);
  vTaskDelete(NULL);
}

static void start_mic_shared(uint32_t rate_hz, uint16_t bits,
                             uint16_t channels) {
  if (bits != 16 && bits != 0) {
    ESP_LOGW(TAG, "Only 16-bit PCM supported; got %u, using 16.",
             (unsigned)bits);
  }
  uint8_t ch = (channels >= 2) ? 2 : 1;

  if (s_mic_task && (s_mic_rate != rate_hz || s_mic_ch != ch)) {
    mic_stop_hw();
  }

  esp_err_t err = i2s_mic_setup(rate_hz, ch);
  if (err != ESP_OK) {
    s_mic_i2s_ok = false;
    ESP_LOGE(TAG, "START_MIC: I2S setup failed; not streaming.");
    return;
  }
  s_mic_i2s_ok = true;
  s_mic_rate = rate_hz;
  s_mic_ch = ch;

  s_mic_run = true;
  if (s_mic_task == NULL) {
    if (xTaskCreate(mic_task, "mic_uart", 4096, NULL, 5, &s_mic_task) !=
        pdPASS) {
      ESP_LOGE(TAG, "mic task create failed");
      s_mic_run = false;
      i2s_mic_teardown();
      s_mic_i2s_ok = false;
    }
  }
}

static void uart_start_mic(uint32_t rate_hz, uint16_t bits, uint16_t channels) {
  s_stream_uart = true;
  start_mic_shared(rate_hz, bits, channels);
}

static void uart_stop_mic(void) {
  s_stream_uart = false;
  if (!s_stream_mcp) {
    mic_stop_hw();
  }
}

static void handle_play(const uint8_t *payload, uint16_t len) {
  if (len < 4) {
    return;
  }
  uint32_t pcm_len = 0;
  memcpy(&pcm_len, payload, 4);
  if (pcm_len > MAX_PLAY_PCM_BYTES || (uint32_t)(len - 4) < pcm_len) {
    ESP_LOGW(TAG, "PLAY_PCM invalid len %u (payload %u)", (unsigned)pcm_len,
             (unsigned)len);
    return;
  }
  if (!s_spk_i2s_ok || s_tx == NULL) {
    ESP_LOGW(TAG, "PLAY_PCM: speaker I2S not ready; dropping.");
    return;
  }
  const uint8_t *pcm = payload + 4;
  size_t written = 0;
  esp_err_t w =
      i2s_channel_write(s_tx, pcm, pcm_len, &written, pdMS_TO_TICKS(1000));
  if (w != ESP_OK || written != pcm_len) {
    ESP_LOGW(TAG, "i2s_channel_write incomplete: %s %u/%u", esp_err_to_name(w),
             (unsigned)written, (unsigned)pcm_len);
  }
}

static void ensure_spk_for_play(uint32_t rate_hz, uint8_t channels) {
  if (s_spk_i2s_ok && s_tx != NULL) {
    return;
  }
  esp_err_t e = i2s_spk_setup(rate_hz, channels);
  s_spk_i2s_ok = (e == ESP_OK);
}

esp_err_t audio_mcp_mcp_subscribe(uint32_t sample_rate_hz, uint8_t channels) {
  uint8_t ch = (channels >= 2) ? 2 : 1;
  if (s_mcp_ringbuf == NULL) {
    s_mcp_ringbuf = xRingbufferCreate(MCP_RINGBUF_BYTES, RINGBUF_TYPE_BYTEBUF);
    if (s_mcp_ringbuf == NULL) {
      return ESP_ERR_NO_MEM;
    }
  }
  s_stream_mcp = true;
  start_mic_shared(sample_rate_hz, 16, ch);
  return s_mic_i2s_ok ? ESP_OK : ESP_FAIL;
}

void audio_mcp_mcp_unsubscribe(void) {
  s_stream_mcp = false;
  vTaskDelay(pdMS_TO_TICKS(50));
  if (!s_stream_uart) {
    mic_stop_hw();
  } else if (s_mcp_ringbuf) {
    vRingbufferDelete(s_mcp_ringbuf);
    s_mcp_ringbuf = NULL;
  }
}

bool audio_mcp_mcp_subscribed(void) { return s_stream_mcp; }

bool audio_mcp_mcp_stream_http_ready(void) {
  return s_stream_mcp && (s_mcp_ringbuf != NULL);
}

bool audio_mcp_mic_task_running(void) { return s_mic_run; }

uint32_t audio_mcp_get_mic_sample_rate(void) { return s_mic_rate; }

uint8_t audio_mcp_get_mic_channels(void) { return s_mic_ch; }

void *audio_mcp_mcp_ringbuf_receive(size_t *item_size, uint32_t wait_ms) {
  if (s_mcp_ringbuf == NULL || item_size == NULL) {
    return NULL;
  }
  return xRingbufferReceive(s_mcp_ringbuf, item_size, pdMS_TO_TICKS(wait_ms));
}

void audio_mcp_mcp_ringbuf_return(void *item) {
  if (s_mcp_ringbuf != NULL && item != NULL) {
    vRingbufferReturnItem(s_mcp_ringbuf, item);
  }
}

esp_err_t audio_mcp_speaker_play_pcm_b64(const char *pcm_base64,
                                         uint32_t sample_rate_hz,
                                         uint8_t channels) {
  if (pcm_base64 == NULL) {
    return ESP_ERR_INVALID_ARG;
  }
  size_t b64_len = strlen(pcm_base64);
  if (b64_len == 0 || b64_len > 48000) {
    return ESP_ERR_INVALID_SIZE;
  }
  size_t olen = 0;
  unsigned char out[36000];
  int br = mbedtls_base64_decode(out, sizeof(out), &olen,
                                 (const unsigned char *)pcm_base64, b64_len);
  if (br != 0 || olen == 0 || olen > sizeof(out)) {
    ESP_LOGW(TAG, "base64 decode failed or too large");
    return ESP_ERR_INVALID_ARG;
  }
  uint8_t ch = (channels >= 2) ? 2 : 1;
  ensure_spk_for_play(sample_rate_hz, ch);
  if (!s_spk_i2s_ok || s_tx == NULL) {
    return ESP_ERR_INVALID_STATE;
  }
  size_t written = 0;
  esp_err_t w =
      i2s_channel_write(s_tx, out, olen, &written, pdMS_TO_TICKS(3000));
  if (w != ESP_OK || written != olen) {
    ESP_LOGW(TAG, "speaker write incomplete: %s", esp_err_to_name(w));
    return ESP_FAIL;
  }
  return ESP_OK;
}

void audio_mcp_init(void) {
  s_uart_tx_mutex = xSemaphoreCreateMutex();
  try_init_i2s_stubs();
  uart_init();
}

void audio_mcp_uart_proto_task(void *pv) {
  enum {
    ST_SYNC0,
    ST_SYNC1,
    ST_CMD,
    ST_LO,
    ST_HI,
    ST_PAYLOAD,
    ST_CRC
  } st = ST_SYNC0;

  uint8_t cmd = 0;
  uint16_t paylen = 0;
  uint16_t paygot = 0;
  uint8_t payload[MAX_PAYLOAD];
  uint8_t crcbuf[3 + MAX_PAYLOAD];
  int crcidx = 0;

  uint8_t ch;
  while (1) {
    int n = uart_read_bytes(UART_PORT, &ch, 1, portMAX_DELAY);
    if (n != 1) {
      continue;
    }

    switch (st) {
    case ST_SYNC0:
      if (ch == SYNC0) {
        st = ST_SYNC1;
      }
      break;
    case ST_SYNC1:
      if (ch == SYNC1) {
        st = ST_CMD;
      } else if (ch == SYNC0) {
        st = ST_SYNC1;
      } else {
        st = ST_SYNC0;
      }
      break;
    case ST_CMD:
      cmd = ch;
      crcidx = 0;
      crcbuf[crcidx++] = cmd;
      st = ST_LO;
      break;
    case ST_LO:
      paylen = ch;
      st = ST_HI;
      break;
    case ST_HI:
      paylen |= ((uint16_t)ch << 8);
      if (paylen > MAX_PAYLOAD) {
        st = ST_SYNC0;
        break;
      }
      crcbuf[crcidx++] = (uint8_t)(paylen & 0xFF);
      crcbuf[crcidx++] = (uint8_t)(paylen >> 8);
      paygot = 0;
      if (paylen == 0) {
        st = ST_CRC;
      } else {
        st = ST_PAYLOAD;
      }
      break;
    case ST_PAYLOAD:
      payload[paygot++] = ch;
      crcbuf[crcidx++] = ch;
      if (paygot >= paylen) {
        st = ST_CRC;
      }
      break;
    case ST_CRC: {
      uint8_t expect = crc8_dallas(crcbuf, (size_t)crcidx);
      if (expect != ch) {
        ESP_LOGW(TAG, "CRC mismatch (cmd 0x%02x)", cmd);
        st = ST_SYNC0;
        break;
      }
      switch (cmd) {
      case CMD_START_MIC:
        if (paylen >= 8) {
          uint32_t rate = 0;
          uint16_t bits = 16, chn = 1;
          memcpy(&rate, payload, 4);
          memcpy(&bits, payload + 4, 2);
          memcpy(&chn, payload + 6, 2);
          uart_start_mic(rate, bits, chn);
        }
        break;
      case CMD_STOP_MIC:
        uart_stop_mic();
        break;
      case CMD_PLAY_PCM:
        if (paylen >= 4) {
          uint32_t rate = s_mic_rate;
          uint8_t chn = (s_mic_ch >= 2) ? 2 : 1;
          ensure_spk_for_play(rate, chn);
        }
        handle_play(payload, paylen);
        break;
      case CMD_STOP_PLAY:
        i2s_spk_teardown();
        s_spk_i2s_ok = false;
        break;
      default:
        ESP_LOGW(TAG, "Unknown CMD 0x%02x", cmd);
        break;
      }
      st = ST_SYNC0;
      break;
    }
    default:
      st = ST_SYNC0;
      break;
    }
  }
}

static void uart_init(void) {
  uart_config_t ucfg = {
      .baud_rate = CONFIG_AUDIO_UART_BAUD,
      .data_bits = UART_DATA_8_BITS,
      .parity = UART_PARITY_DISABLE,
      .stop_bits = UART_STOP_BITS_1,
      .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
      .source_clk = UART_SCLK_DEFAULT,
  };
  ESP_ERROR_CHECK(uart_driver_install(UART_PORT, UART_BUF_SZ, UART_BUF_SZ,
                                      UART_QUEUE_SIZE, NULL, 0));
  ESP_ERROR_CHECK(uart_param_config(UART_PORT, &ucfg));
  ESP_ERROR_CHECK(uart_set_pin(UART_PORT, UART_PIN_NO_CHANGE,
                               UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE,
                               UART_PIN_NO_CHANGE));
  ESP_LOGI(TAG, "UART%d @ %d baud (protocol)", UART_PORT,
           CONFIG_AUDIO_UART_BAUD);
}
