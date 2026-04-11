/*
 * Minimal MCP (JSON-RPC) over HTTP for ESP32-S3: tools/list, tools/call,
 * initialize. Audio: mic subscribe + PCM stream GET; speaker play via base64.
 */

#include "mcp_http.h"

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "audio_mcp.h"
#include "cJSON.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_netif_ip_event.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "nvs_flash.h"
#include "sdkconfig.h"
#include "wifi_credentials.h"

static const char *TAG = "mcp_http";

#define WIFI_CONNECTED_BIT BIT0

static EventGroupHandle_t s_wifi_ev;
static esp_netif_t *s_sta = NULL;
static httpd_handle_t s_httpd = NULL;

static void wifi_event_handler(void *arg, esp_event_base_t base, int32_t id,
                               void *data) {
  if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
    esp_wifi_connect();
  } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
    xEventGroupClearBits(s_wifi_ev, WIFI_CONNECTED_BIT);
    esp_wifi_connect();
    ESP_LOGW(TAG, "WiFi disconnected, retrying…");
  } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
    xEventGroupSetBits(s_wifi_ev, WIFI_CONNECTED_BIT);
    const ip_event_got_ip_t *ev = (const ip_event_got_ip_t *)data;
    const uint8_t *o = (const uint8_t *)&ev->ip_info.ip.addr;
    ESP_LOGI(TAG, "Got IP: %u.%u.%u.%u", (unsigned)o[0], (unsigned)o[1],
             (unsigned)o[2], (unsigned)o[3]);
  }
}

static esp_err_t wifi_init_sta(void) {
  s_wifi_ev = xEventGroupCreate();
  ESP_ERROR_CHECK(esp_netif_init());
  ESP_ERROR_CHECK(esp_event_loop_create_default());
  s_sta = esp_netif_create_default_wifi_sta();

  wifi_init_config_t wcfg = WIFI_INIT_CONFIG_DEFAULT();
  ESP_ERROR_CHECK(esp_wifi_init(&wcfg));

  esp_event_handler_instance_t inst_any;
  esp_event_handler_instance_t inst_got_ip;
  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, &inst_any));
  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, &inst_got_ip));

  wifi_config_t cfg = {0};
  strncpy((char *)cfg.sta.ssid, MCP_WIFI_SSID_VALUE, sizeof(cfg.sta.ssid) - 1);
  strncpy((char *)cfg.sta.password, MCP_WIFI_PASSWORD_VALUE,
          sizeof(cfg.sta.password) - 1);
  cfg.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;

  ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
  ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &cfg));
  ESP_ERROR_CHECK(esp_wifi_start());

  EventBits_t bits = xEventGroupWaitBits(s_wifi_ev, WIFI_CONNECTED_BIT, pdFALSE,
                                         pdTRUE, pdMS_TO_TICKS(60000));
  if ((bits & WIFI_CONNECTED_BIT) == 0) {
    ESP_LOGE(TAG, "WiFi connect timeout");
    return ESP_ERR_TIMEOUT;
  }
  return ESP_OK;
}

static void stream_url(char *out, size_t out_len) {
  esp_netif_ip_info_t ip;
  if (s_sta == NULL || esp_netif_get_ip_info(s_sta, &ip) != ESP_OK) {
    snprintf(out, out_len, "http://127.0.0.1:%d/mcp/stream/mic",
             CONFIG_MCP_HTTP_PORT);
    return;
  }
  snprintf(out, out_len, "http://" IPSTR ":%d/mcp/stream/mic", IP2STR(&ip.ip),
           CONFIG_MCP_HTTP_PORT);
}

static esp_err_t send_json(httpd_req_t *req, cJSON *root) {
  char *s = cJSON_PrintUnformatted(root);
  cJSON_Delete(root);
  if (!s) {
    return httpd_resp_send_500(req);
  }
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_type(req, "application/json; charset=utf-8");
  esp_err_t e = httpd_resp_send(req, s, HTTPD_RESP_USE_STRLEN);
  free(s);
  return e;
}

static cJSON *rpc_envelope_ok(cJSON *id, cJSON *result) {
  cJSON *o = cJSON_CreateObject();
  cJSON_AddStringToObject(o, "jsonrpc", "2.0");
  if (id != NULL) {
    cJSON_AddItemToObject(o, "id", cJSON_Duplicate(id, true));
  } else {
    cJSON_AddNullToObject(o, "id");
  }
  cJSON_AddItemToObject(o, "result", result);
  return o;
}

static cJSON *rpc_err(int code, const char *msg, cJSON *id) {
  cJSON *o = cJSON_CreateObject();
  cJSON_AddStringToObject(o, "jsonrpc", "2.0");
  if (id != NULL) {
    cJSON_AddItemToObject(o, "id", cJSON_Duplicate(id, true));
  } else {
    cJSON_AddNullToObject(o, "id");
  }
  cJSON *e = cJSON_CreateObject();
  cJSON_AddNumberToObject(e, "code", code);
  cJSON_AddStringToObject(e, "message", msg);
  cJSON_AddItemToObject(o, "error", e);
  return o;
}

static cJSON *tools_list_result(void) {
  cJSON *tools = cJSON_CreateArray();

  cJSON *t1 = cJSON_CreateObject();
  cJSON_AddStringToObject(t1, "name", "esp32_audio_mic_subscribe");
  cJSON_AddStringToObject(t1, "description",
                          "开启麦克风 PCM 采集；订阅后请用 GET stream_url "
                          "拉流（s16le，与 X-Sample-Rate 头一致）。");
  cJSON *s1 = cJSON_Parse(
      "{\"type\":\"object\",\"properties\":{\"sample_rate\":{\"type\":"
      "\"integer\","
      "\"default\":16000},\"channels\":{\"type\":\"integer\",\"minimum\":1,"
      "\"maximum\":2,\"default\":1}}}");
  cJSON_AddItemToObject(t1, "inputSchema", s1 ? s1 : cJSON_CreateObject());
  cJSON_AddItemToArray(tools, t1);

  cJSON *t2 = cJSON_CreateObject();
  cJSON_AddStringToObject(t2, "name", "esp32_audio_mic_unsubscribe");
  cJSON_AddStringToObject(t2, "description", "停止麦克风 MCP 订阅并释放流。");
  cJSON *s2 = cJSON_Parse("{\"type\":\"object\",\"properties\":{}}");
  cJSON_AddItemToObject(t2, "inputSchema", s2 ? s2 : cJSON_CreateObject());
  cJSON_AddItemToArray(tools, t2);

  cJSON *t3 = cJSON_CreateObject();
  cJSON_AddStringToObject(t3, "name", "esp32_audio_speaker_play_pcm");
  cJSON_AddStringToObject(t3, "description",
                          "将 base64 编码的 s16le PCM 送到扬声器播放。");
  cJSON *s3 =
      cJSON_Parse("{\"type\":\"object\",\"required\":[\"pcm_base64\"],"
                  "\"properties\":{\"pcm_base64\":{\"type\":\"string\"},"
                  "\"sample_rate\":{\"type\":\"integer\",\"default\":16000},"
                  "\"channels\":{\"type\":\"integer\",\"minimum\":1,"
                  "\"maximum\":2,\"default\":1}}}");
  cJSON_AddItemToObject(t3, "inputSchema", s3 ? s3 : cJSON_CreateObject());
  cJSON_AddItemToArray(tools, t3);

  cJSON *res = cJSON_CreateObject();
  cJSON_AddItemToObject(res, "tools", tools);
  return res;
}

static cJSON *tool_result_text(const char *text) {
  cJSON *res = cJSON_CreateObject();
  cJSON *content = cJSON_CreateArray();
  cJSON *item = cJSON_CreateObject();
  cJSON_AddStringToObject(item, "type", "text");
  cJSON_AddStringToObject(item, "text", text);
  cJSON_AddItemToArray(content, item);
  cJSON_AddItemToObject(res, "content", content);
  cJSON_AddBoolToObject(res, "isError", false);
  return res;
}

static esp_err_t handle_tools_call(cJSON *id, cJSON *params, httpd_req_t *req) {
  cJSON *name = cJSON_GetObjectItem(params, "name");
  if (!cJSON_IsString(name)) {
    return send_json(req, rpc_err(-32602, "Invalid params", id));
  }
  cJSON *args = cJSON_GetObjectItem(params, "arguments");
  if (args == NULL) {
    args = cJSON_CreateObject();
  }

  if (strcmp(name->valuestring, "esp32_audio_mic_subscribe") == 0) {
    uint32_t rate = 16000;
    int ch = 1;
    cJSON *r = cJSON_GetObjectItem(args, "sample_rate");
    cJSON *c = cJSON_GetObjectItem(args, "channels");
    if (cJSON_IsNumber(r)) {
      rate = (uint32_t)r->valuedouble;
    }
    if (cJSON_IsNumber(c)) {
      ch = (int)c->valuedouble;
    }
    esp_err_t e = audio_mcp_mcp_subscribe(rate, (uint8_t)ch);
    if (e != ESP_OK) {
      return send_json(req, rpc_err(-32000, "mic subscribe failed", id));
    }
    char url[160];
    stream_url(url, sizeof(url));
    char msg[384];
    snprintf(msg, sizeof(msg),
             "stream_url=%s sample_rate=%" PRIu32
             " channels=%d format=s16le (GET stream_url for raw PCM)",
             url, rate, ch);
    return send_json(req, rpc_envelope_ok(id, tool_result_text(msg)));
  }

  if (strcmp(name->valuestring, "esp32_audio_mic_unsubscribe") == 0) {
    audio_mcp_mcp_unsubscribe();
    return send_json(req,
                     rpc_envelope_ok(id, tool_result_text("{\"ok\":true}")));
  }

  if (strcmp(name->valuestring, "esp32_audio_speaker_play_pcm") == 0) {
    cJSON *b64 = cJSON_GetObjectItem(args, "pcm_base64");
    if (!cJSON_IsString(b64)) {
      return send_json(req, rpc_err(-32602, "pcm_base64 required", id));
    }
    uint32_t rate = 16000;
    int ch = 1;
    cJSON *r = cJSON_GetObjectItem(args, "sample_rate");
    cJSON *c = cJSON_GetObjectItem(args, "channels");
    if (cJSON_IsNumber(r)) {
      rate = (uint32_t)r->valuedouble;
    }
    if (cJSON_IsNumber(c)) {
      ch = (int)c->valuedouble;
    }
    esp_err_t e =
        audio_mcp_speaker_play_pcm_b64(b64->valuestring, rate, (uint8_t)ch);
    if (e != ESP_OK) {
      return send_json(req, rpc_err(-32000, "speaker play failed", id));
    }
    return send_json(req,
                     rpc_envelope_ok(id, tool_result_text("{\"ok\":true}")));
  }

  return send_json(req, rpc_err(-32601, "Unknown tool", id));
}

static esp_err_t handle_initialize(cJSON *id, httpd_req_t *req) {
  cJSON *res = cJSON_CreateObject();
  cJSON_AddStringToObject(res, "protocolVersion", "2024-11-05");
  cJSON *caps = cJSON_CreateObject();
  cJSON *tools = cJSON_CreateObject();
  cJSON_AddItemToObject(caps, "tools", tools);
  cJSON_AddItemToObject(res, "capabilities", caps);
  cJSON *info = cJSON_CreateObject();
  cJSON_AddStringToObject(info, "name", "esp32s3-audio-mcp");
  cJSON_AddStringToObject(info, "version", "1.0.0");
  cJSON_AddItemToObject(res, "serverInfo", info);
  return send_json(req, rpc_envelope_ok(id, res));
}

static esp_err_t mcp_post_handler(httpd_req_t *req) {
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  size_t len = req->content_len;
  if (len == 0 || len > 65536) {
    cJSON *id = NULL;
    cJSON *err = rpc_err(-32700, "Invalid JSON body size", id);
    return send_json(req, err);
  }

  char *buf = malloc(len + 1);
  if (!buf) {
    return httpd_resp_send_500(req);
  }
  int r = httpd_req_recv(req, buf, len);
  if (r <= 0) {
    free(buf);
    return httpd_resp_send_500(req);
  }
  buf[r] = '\0';

  cJSON *root = cJSON_Parse(buf);
  free(buf);
  if (!root) {
    return send_json(req, rpc_err(-32700, "Parse error", NULL));
  }

  cJSON *id = cJSON_GetObjectItem(root, "id");
  cJSON *method = cJSON_GetObjectItem(root, "method");
  if (!cJSON_IsString(method)) {
    cJSON_Delete(root);
    return send_json(req, rpc_err(-32600, "Invalid Request", id));
  }

  const char *m = method->valuestring;

  if (strcmp(m, "notifications/initialized") == 0 ||
      strncmp(m, "notifications/", 14) == 0) {
    cJSON_Delete(root);
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_status(req, "204 No Content");
    return httpd_resp_send(req, NULL, 0);
  }

  if (strcmp(m, "initialize") == 0) {
    esp_err_t e = handle_initialize(id, req);
    cJSON_Delete(root);
    return e;
  }

  if (strcmp(m, "tools/list") == 0) {
    cJSON *res = tools_list_result();
    cJSON *out = rpc_envelope_ok(id, res);
    cJSON_Delete(root);
    return send_json(req, out);
  }

  if (strcmp(m, "tools/call") == 0) {
    cJSON *params = cJSON_GetObjectItem(root, "params");
    if (!cJSON_IsObject(params)) {
      cJSON_Delete(root);
      return send_json(req, rpc_err(-32602, "Invalid params", id));
    }
    esp_err_t e = handle_tools_call(id, params, req);
    cJSON_Delete(root);
    return e;
  }

  if (strcmp(m, "ping") == 0) {
    cJSON *res = cJSON_CreateObject();
    cJSON *out = rpc_envelope_ok(id, res);
    cJSON_Delete(root);
    return send_json(req, out);
  }

  cJSON_Delete(root);
  return send_json(req, rpc_err(-32601, "Method not found", id));
}

static esp_err_t mcp_options_handler(httpd_req_t *req) {
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Methods", "POST, GET, OPTIONS");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Headers",
                     "Content-Type, Accept");
  httpd_resp_set_status(req, "204 No Content");
  return httpd_resp_send(req, NULL, 0);
}

static esp_err_t stream_options_handler(httpd_req_t *req) {
  return mcp_options_handler(req);
}

static esp_err_t mcp_stream_mic_get_handler(httpd_req_t *req) {
  if (!audio_mcp_mcp_stream_http_ready()) {
    httpd_resp_set_status(req, "503 Service Unavailable");
    httpd_resp_set_type(req, "text/plain");
    return httpd_resp_send(req, "mic not subscribed", HTTPD_RESP_USE_STRLEN);
  }

  char rate_str[16];
  snprintf(rate_str, sizeof(rate_str), "%" PRIu32,
           audio_mcp_get_mic_sample_rate());
  httpd_resp_set_status(req, HTTPD_200);
  httpd_resp_set_type(req, "application/octet-stream");
  httpd_resp_set_hdr(req, "X-Sample-Rate", rate_str);
  httpd_resp_set_hdr(req, "X-Channels",
                     (audio_mcp_get_mic_channels() >= 2) ? "2" : "1");
  httpd_resp_set_hdr(req, "X-PCM-Format", "s16le");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");

  while (audio_mcp_mcp_subscribed() && audio_mcp_mic_task_running()) {
    size_t item_size = 0;
    void *data = audio_mcp_mcp_ringbuf_receive(&item_size, 500);
    if (data == NULL) {
      continue;
    }
    esp_err_t e = httpd_resp_send_chunk(req, data, item_size);
    audio_mcp_mcp_ringbuf_return(data);
    if (e != ESP_OK) {
      break;
    }
  }
  (void)httpd_resp_send_chunk(req, NULL, 0);
  return ESP_OK;
}

static const httpd_uri_t uri_mcp_post = {
    .uri = "/mcp",
    .method = HTTP_POST,
    .handler = mcp_post_handler,
    .user_ctx = NULL,
};

static const httpd_uri_t uri_mcp_opts = {
    .uri = "/mcp",
    .method = HTTP_OPTIONS,
    .handler = mcp_options_handler,
    .user_ctx = NULL,
};

static const httpd_uri_t uri_stream_get = {
    .uri = "/mcp/stream/mic",
    .method = HTTP_GET,
    .handler = mcp_stream_mic_get_handler,
    .user_ctx = NULL,
};

static const httpd_uri_t uri_stream_opts = {
    .uri = "/mcp/stream/mic",
    .method = HTTP_OPTIONS,
    .handler = stream_options_handler,
    .user_ctx = NULL,
};

void mcp_http_start(void) {
  esp_err_t ret = nvs_flash_init();
  if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
      ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    ret = nvs_flash_init();
  }
  ESP_ERROR_CHECK(ret);

  if (strlen(MCP_WIFI_SSID_VALUE) == 0) {
    ESP_LOGW(
        TAG,
        "MCP_WIFI_SSID empty; skip WiFi/MCP HTTP. Set menuconfig MCP WiFi.");
    return;
  }

  if (wifi_init_sta() != ESP_OK) {
    ESP_LOGE(TAG, "WiFi failed; MCP HTTP disabled.");
    return;
  }

  httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
  cfg.server_port = CONFIG_MCP_HTTP_PORT;
  cfg.stack_size = 8192;
  cfg.max_uri_handlers = 12;
  cfg.lru_purge_enable = true;

  if (httpd_start(&s_httpd, &cfg) != ESP_OK) {
    ESP_LOGE(TAG, "httpd_start failed");
    return;
  }

  httpd_register_uri_handler(s_httpd, &uri_mcp_post);
  httpd_register_uri_handler(s_httpd, &uri_mcp_opts);
  httpd_register_uri_handler(s_httpd, &uri_stream_get);
  httpd_register_uri_handler(s_httpd, &uri_stream_opts);

  ESP_LOGI(TAG, "MCP HTTP on port %d — POST /mcp, GET /mcp/stream/mic",
           CONFIG_MCP_HTTP_PORT);
}
