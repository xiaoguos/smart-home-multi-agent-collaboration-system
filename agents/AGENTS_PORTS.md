# Agent 端口配置说明

本文档说明了所有 agent 的端口分配和通信关系。

## 端口分配

| Agent 名称 | 端口 | 目录 | 描述 |
|-----------|------|------|------|
| Conductor Agent | 12000 | `conductor_agent/` | 中央管家，协调所有其他 agent |
| Air Conditioner Agent | 12001 | `air_conditioner_agent/` | 空调控制 agent |
| Air Cleaner Agent | 12002 | `air_cleaner_agent/` | 空气净化器控制 agent |
| Data Mining Agent | 12003 | `dw_agent/` | 数据挖掘和分析 agent |

## 启动顺序

建议按以下顺序启动 agent：

1. **首先启动各个功能 agent**（可并行）：
   ```bash
   # 启动空调 agent
   cd agents/air_conditioner_agent
   python main.py --host localhost --port 12001
   
   # 启动空气净化器 agent
   cd agents/air_cleaner_agent
   python main.py --host localhost --port 12002
   
   # 启动数据挖掘 agent（如果有）
   cd agents/dw_agent
   python main.py --host localhost --port 12003
   ```

2. **最后启动中央管家 agent**：
   ```bash
   cd agents/conductor_agent
   python main.py --host localhost --port 12000
   ```

## 通信关系

```
┌─────────────────────────┐
│   Conductor Agent       │
│   (Port 12000)          │
│   中央管家              │
└───────┬─────────────────┘
        │
        ├──────────────────────┬──────────────────────┬─────────────────────┐
        │                      │                      │                     │
        ▼                      ▼                      ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Air Cond.    │    │ Air Cleaner  │    │ Data Mining  │    │ (其他 agent) │
│ Agent        │    │ Agent        │    │ Agent        │    │              │
│ Port 12001   │    │ Port 12002   │    │ Port 12003   │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

## Agent 功能说明

### Conductor Agent (中央管家)
- **端口**: 12000
- **功能**: 
  - 管理和协调所有子 agent
  - 提供统一的设备控制接口
  - 记录所有操作日志到 SQLite 数据库
  - 分析用户行为并提供个性化建议
- **工具**:
  - `list_available_agents`: 列出所有可用代理
  - `execute_agent_command`: 向指定代理发送命令
  - `get_agent_status`: 检查代理运行状态
  - `control_device`: 控制智能设备（推荐）
  - `get_system_overview`: 获取系统概览
  - `analyze_user_behavior`: 分析用户行为
  - `get_user_insights`: 获取用户洞察

### Air Conditioner Agent (空调控制)
- **端口**: 12001
- **设备**: lumi.acpartner.mcn02
- **功能**:
  - 控制空调电源开关
  - 设置目标温度（16-30°C）
  - 查询空调状态
- **工具**:
  - `get_ac_status`: 获取空调状态
  - `set_ac_power`: 开关空调
  - `set_ac_temperature`: 设置温度

### Air Cleaner Agent (空气净化器控制)
- **端口**: 12002
- **设备**: zhimi.airp.oa1 (桌面空气净化器)
- **协议**: MIoT
- **功能**:
  - 控制净化器电源开关
  - 设置风扇等级（1-3档）
  - 切换工作模式（自动/睡眠/喜爱）
  - 调节LED亮度
  - 监测PM2.5、湿度
  - 查看滤芯寿命
- **工具**:
  - `get_purifier_status`: 获取净化器状态
  - `set_purifier_power`: 开关净化器
  - `set_purifier_fan_level`: 设置风扇等级
  - `set_purifier_mode`: 设置工作模式
  - `set_purifier_led`: 设置LED亮度

## 使用示例

### 通过中央管家控制设备

```python
# 控制空调
control_device(
    device_type="air_conditioner",
    action="开启空调",
    parameters={}
)

# 设置空调温度
control_device(
    device_type="air_conditioner",
    action="设置温度到25度",
    parameters={"temperature": 25}
)

# 控制空气净化器
control_device(
    device_type="air_cleaner",
    action="开启空气净化器",
    parameters={}
)

# 设置净化器为睡眠模式
control_device(
    device_type="air_cleaner",
    action="设置为睡眠模式",
    parameters={}
)
```

## 故障排查

### Agent 无法启动
1. 检查端口是否被占用
2. 确认所有依赖已安装：`pip install -r requirements.txt`
3. 检查日志输出

### 中央管家无法连接子 agent
1. 确认子 agent 已启动并监听正确端口
2. 检查防火墙设置
3. 验证端口配置是否正确（参考本文档）
4. 查看 conductor_agent 的日志

### 设备控制失败
1. 检查设备 IP 和 token 是否正确
2. 确认设备在线且可访问
3. 验证设备型号是否正确配置
4. 对于空气净化器，确保使用 MIoT 协议

## 配置文件位置

- Conductor Agent 配置: `agents/conductor_agent/tools.py` (REGISTERED_AGENTS)
- Air Conditioner Agent 设备配置: `agents/air_conditioner_agent/tools.py`
- Air Cleaner Agent 设备配置: `agents/air_cleaner_agent/tools.py`

## 日志和数据库

- Conductor Agent 操作日志: `agents/conductor_agent/user_behavior.db`
- 日志级别: INFO (可在各 agent 的 main.py 中修改)

