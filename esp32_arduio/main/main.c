#include "audio_mcp.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "mcp_http.h"

static const char *TAG = "main";

void app_main(void)
{
    audio_mcp_init();
    mcp_http_start();

    if (xTaskCreate(audio_mcp_uart_proto_task, "uart_proto", 8192, NULL, 6, NULL) != pdPASS) {
        ESP_LOGE(TAG, "uart_proto task create failed");
    }
}
