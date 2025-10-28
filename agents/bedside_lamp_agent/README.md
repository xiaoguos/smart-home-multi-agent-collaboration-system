# Bedside Lamp Agent

Moss AI 床头灯控制系统，专门负责 Yeelink 床头灯（yeelink.light.bslamp2）的智能控制。

## 功能特性

- 💡 电源控制（开/关）
- 🌟 亮度调节（0-100%）
- 🌡️ 色温设置（暖光/冷光）
- 🎨 颜色设置（RGB）
- 🎭 场景模式
  - 📖 阅读模式
  - 😴 睡眠模式
  - 💑 浪漫模式
  - 🌙 夜灯模式

## 快速开始

### 安装依赖

使用 uv（推荐）：
```bash
cd agents/bedside_lamp_agent
uv sync
```

### 启动服务

使用 uv：
```bash
uv run .
```

或使用 Python 模块方式：
```bash
python -m .
```

或运行 main.py：
```bash
python main.py
```

### 命令行参数

```bash
# 指定主机和端口
uv run . --host 0.0.0.0 --port 12001
```

## 配置

服务配置通过项目根目录的 `config.yaml` 文件管理：

```yaml
agents:
  bedside_lamp:
    host: "0.0.0.0"
    port: 12001
```

## 设备配置

需要在 `config.yaml` 中配置床头灯的 IP 和 Token：

```yaml
xiaomi_devices:
  bedside_lamp:
    ip: "192.168.1.100"
    token: "your_device_token"
    model: "yeelink.light.bslamp2"
```

## 使用示例

- "打开床头灯"
- "调到50%亮度"
- "设置暖光"
- "变成粉色"
- "切换到阅读模式"
- "关闭床头灯"

## 依赖

- a2a: Agent-to-Agent 协议支持
- click: 命令行接口
- uvicorn: ASGI 服务器
- httpx: HTTP 客户端
- PyYAML: YAML 配置解析
- python-miio: 小米设备控制库

