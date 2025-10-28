# Conductor Agent

Moss AI 智能家居总管理系统，负责协调和管理所有智能设备代理。

## 功能特性

- 🎯 智能设备代理协调
- 🔍 代理发现和管理
- 📊 系统状态监控
- 🤖 智能任务调度
- 📝 使用习惯分析
- 💡 个性化建议

## 快速开始

### 安装依赖

使用 uv（推荐）：
```bash
cd agents/conductor_agent
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
uv run . --host 0.0.0.0 --port 12000

# 启用 debug 模式（兼容 PyCharm debugger）
uv run . --debug
```

## 配置

服务配置通过项目根目录的 `config.yaml` 文件管理：

```yaml
agents:
  conductor:
    host: "0.0.0.0"
    port: 12000
```

## API 端点

启动服务后，Agent 提供以下能力：
- 智能家居设备管理
- 多代理协调
- 任务执行和调度
- 状态查询和监控

## 依赖

- a2a: Agent-to-Agent 协议支持
- click: 命令行接口
- uvicorn: ASGI 服务器
- httpx: HTTP 客户端
- PyYAML: YAML 配置解析

