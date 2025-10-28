# Air Conditioner Agent

Moss AI 空调控制系统，专门负责家庭空调系统的智能控制。

## 功能特性

- ⚡ 电源控制（开/关）
- 🌡️ 温度调节
- 🔄 模式切换
  - ❄️ 制冷模式
  - 🔥 制热模式
  - 💨 送风模式
  - 💧 除湿模式
- 🌪️ 风速调节
- 📊 状态查询

## 快速开始

### 安装依赖

使用 uv（推荐）：
```bash
cd agents/air_conditioner_agent
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
uv run . --host 0.0.0.0 --port 12002
```

## 配置

服务配置通过项目根目录的 `config.yaml` 文件管理：

```yaml
agents:
  air_conditioner:
    host: "0.0.0.0"
    port: 12002
```

## 设备配置

需要在 `config.yaml` 中配置空调的 IP 和 Token：

```yaml
xiaomi_devices:
  air_conditioner:
    ip: "192.168.1.101"
    token: "your_device_token"
    model: "xiaomi.aircondition.xxx"
```

## 使用示例

- "打开空调"
- "设置温度为 22 度"
- "切换到制冷模式"
- "调高风速"
- "关闭空调"

## 依赖

- a2a: Agent-to-Agent 协议支持
- click: 命令行接口
- uvicorn: ASGI 服务器
- httpx: HTTP 客户端
- PyYAML: YAML 配置解析
- python-miio: 小米设备控制库

