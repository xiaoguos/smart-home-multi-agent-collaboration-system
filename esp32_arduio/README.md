# Arduio_MCP — ESP32-S3 音频 MCP（HTTP）与 UART 协议

固件在 **ESP32-S3** 上同时提供：

1. **MCP over HTTP**：JSON-RPC（`initialize` / `tools/list` / `tools/call`），用于麦克风 PCM 订阅与扬声器播放大模型返回的 PCM。
2. **UART 二进制协议**：与上位机串口通信时的帧格式（与原有设计兼容）。

业务代码位于 `main/audio_mcp.c`（I2S + UART + MCP 环形缓冲）、`main/mcp_http.c`（WiFi + HTTP + JSON-RPC），`main/main.c` 仅负责启动。

---

## 环境要求

- [ESP-IDF](https://docs.espressif.com/projects/esp-idf/) 5.x（工程 `sdkconfig.defaults` 目标为 `esp32s3`）
- Python、`idf.py` 已按官方文档完成安装与 `export`

```bash
cd /path/to/Arduio_MCP
idf.py set-target esp32s3
idf.py menuconfig   # 见下文配置项
idf.py build flash monitor
```

---

## menuconfig 配置

### Audio / UART binary protocol

| 项 | 说明 |
|----|------|
| **UART baud rate** | 默认 `921600`，与上位机工具一致 |
| **I2S MIC / SPK port** | 麦克风和扬声器须使用 **不同** I2S 外设（默认 MIC=I2S0，SPK=I2S1） |
| **GPIO** | 按实际板子连接修改 BCLK / WS / DIN / DOUT（默认示例：Mic 4/5/6，Speaker 7/8/9） |

### MCP over HTTP / WiFi

| 项 | 说明 |
|----|------|
| **MCP_WIFI_SSID** | 路由器 SSID。**留空则不启动 WiFi 与 HTTP MCP**，仅 UART 协议可用 |
| **MCP_WIFI_PASSWORD** | WiFi 密码 |
| **MCP_HTTP_PORT** | HTTP 服务端口，默认 **8080** |

---

## 硬件接线（默认示例）

典型 **ESP32-S3-DevKitC-1** 外接 I2S 麦克风与功放：

- 麦克风（I2S0）：BCLK=GPIO4，WS=GPIO5，DIN=GPIO6  
- 扬声器（I2S1）：BCLK=GPIO7，WS=GPIO8，DOUT=GPIO9  

请以 `menuconfig` 中实际 GPIO 为准。

---

## 使用方式一：MCP（HTTP JSON-RPC）

设备连上 WiFi 后，日志中会打印分配的 IP。假设 IP 为 `192.168.1.100`、端口为 `8080`。

### 端点

| 方法 | 路径 | 作用 |
|------|------|------|
| `POST` | `http://<设备IP>:<端口>/mcp` | JSON-RPC：初始化、列工具、调用工具 |
| `GET` | `http://<设备IP>:<端口>/mcp/stream/mic` | 订阅麦克风后拉取 **原始 PCM**（见下） |
| `OPTIONS` | 同上 | CORS 预检 |

麦克风流为 **s16le**，采样率与声道见响应头：`X-Sample-Rate`、`X-Channels`、`X-PCM-Format: s16le`。

### 推荐流程

1. **调用工具** `esp32_audio_mic_subscribe`  
   - 参数示例：`sample_rate`（如 `16000`）、`channels`（`1` 或 `2`）。  
   - 返回的文本中会说明 **`stream_url`**（与 `GET .../mcp/stream/mic` 一致）。
2. **HTTP GET** 上一步的流地址，持续读取二进制 PCM（供 ASR / 大模型等使用）。
3. 需要播音时，调用 **`esp32_audio_speaker_play_pcm`**：  
   - `pcm_base64`：s16le PCM 的 Base64；  
   - `sample_rate`、`channels` 与数据一致。
4. 结束麦克风：**`esp32_audio_mic_unsubscribe`**。  
   - 建议 **先断开 GET 流**，再取消订阅，避免与缓冲区生命周期冲突。

### JSON-RPC 示例（curl）

**initialize：**

```bash
curl -s -X POST "http://192.168.1.100:8080/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'
```

**列出工具：**

```bash
curl -s -X POST "http://192.168.1.100:8080/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

**订阅麦克风并开始拉流（另开终端）：**

```bash
# 先 tools/call esp32_audio_mic_subscribe（略），再：
curl -s "http://192.168.1.100:8080/mcp/stream/mic" -o mic.pcm
```

### 与 Cursor / 桌面 MCP（stdio）的关系

常见 MCP 客户端走 **stdio**。本固件是 **HTTP**。若要让编辑器直连，需在 PC 上增加一层 **stdio ↔ HTTP** 的小代理（本仓库未包含）。你也可以在自有脚本里用 `curl`/HTTP 客户端直接调上述接口。

---

## 使用方式二：UART 二进制协议

与串口工具/脚本约定帧格式（默认 **UART0**、波特率见 `menuconfig`）：

**主机 → 设备**

- 帧：`0xA5 0x5A | CMD(u8) | LEN(u16 LE) | PAYLOAD | CRC8`  
- CRC8：Dallas/Maxim，覆盖 `[CMD][LEN_LO][LEN_HI][PAYLOAD...]`  

| CMD | 说明 |
|-----|------|
| `0x01` START_MIC | 载荷：`sample_rate_hz(u32 LE)`, `bits(u16 LE)`, `channels(u16 LE)` |
| `0x02` STOP_MIC | 停止麦克风 |
| `0x10` PLAY_PCM | 载荷：`pcm_len(u32 LE)` + PCM 字节 |
| `0x11` STOP_PLAY | 停止播放 |

**设备 → 主机（麦克风 PCM）**

- `0xB5 0x5B | 0x01 | pcm_total_len(u32 LE) | PCM`

若已启用 MCP 麦克风订阅，UART 与 HTTP 流可同时从同一麦克风采数（实现上为双路输出，注意带宽）。

---

## 常见问题

- **未配置 WiFi SSID**：不启动 HTTP，仅串口协议可用；需要 MCP 时请在 `menuconfig` 填写 SSID/密码并重新烧录。  
- **连接 WiFi 失败**：检查 SSID/密码、2.4G、路由器黑名单与信号。  
- **GET `/mcp/stream/mic` 返回 503**：先成功执行 `esp32_audio_mic_subscribe`。  
- **扬声器无声音**：确认 I2S 引脚、功放使能、PCM 格式为 **16-bit s16le**，且 `sample_rate`/`channels` 与数据一致。

---

## 仓库结构（main）

| 文件 | 作用 |
|------|------|
| `main.c` | `app_main`：初始化音频、启动 MCP HTTP、UART 协议任务 |
| `audio_mcp.c` | I2S、UART 帧、MCP 麦克风流环形缓冲、扬声器 Base64 播放 |
| `mcp_http.c` | WiFi Station、HTTP 服务、MCP JSON-RPC 与流 URI 注册 |

---

## 许可与免责

硬件与网络环境差异较大，GPIO 与 WiFi 请以实测为准；生产环境请自行加固鉴权（HTTPS、Token 等），本示例未内置身份验证。
