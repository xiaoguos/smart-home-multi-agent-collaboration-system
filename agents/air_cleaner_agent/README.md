# Air Cleaner Agent

Moss AI 空气净化器控制系统，专门负责桌面空气净化器（zhimi-oa1）的智能控制。

## 功能特性

- ⚡ 电源控制（开/关）
- 🌪️ 风扇等级调节
- 🔄 工作模式切换
  - 🤖 自动模式
  - 😴 睡眠模式
  - 🌟 最爱模式
- 💡 LED 亮度控制
- 📊 环境监测
  - PM2.5 浓度
  - 湿度
  - 温度
- 🔍 滤芯寿命查询
- 📈 空气质量分析

## 快速开始

### 安装依赖

使用 uv（推荐）：
```bash
cd agents/air_cleaner_agent
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
uv run . --host 0.0.0.0 --port 12003
```

## 配置

服务配置通过项目根目录的 `config.yaml` 文件管理：

```yaml
agents:
  air_cleaner:
    host: "0.0.0.0"
    port: 12003
```

## 设备配置

需要在 `config.yaml` 中配置空气净化器的 IP 和 Token：

```yaml
xiaomi_devices:
  air_purifier:
    ip: "192.168.1.102"
    token: "your_device_token"
    model: "zhimi.airpurifier.oa1"
```

## 使用示例

- "打开空气净化器"
- "查询当前 PM2.5"
- "设置为睡眠模式"
- "把风扇调到高速"
- "关闭 LED 灯"
- "查看滤芯剩余寿命"

## 依赖

- a2a: Agent-to-Agent 协议支持
- click: 命令行接口
- uvicorn: ASGI 服务器
- httpx: HTTP 客户端
- PyYAML: YAML 配置解析
- python-miio: 小米设备控制库

