# 智能家居总管理代理 (Conductor Agent)

## 概述

总管理代理是一个基于LangChain和A2A架构的智能家居管理系统，负责协调和管理所有智能设备代理。它提供了统一的接口来控制和管理整个智能家居生态系统。

## 功能特性

### 🎯 核心功能
- **代理管理**: 管理多个智能设备代理（空调、空气净化器等）
- **设备控制**: 提供统一的智能设备控制接口
- **系统监控**: 实时监控所有代理的运行状态
- **状态查询**: 获取系统和设备的详细状态信息
- **命令协调**: 向特定代理发送命令并处理响应

### 🛠️ 可用工具
1. `list_available_agents` - 列出所有可用的代理服务
2. `execute_agent_command` - 向指定代理发送命令
3. `get_agent_status` - 获取所有代理的运行状态
4. `control_device` - 控制智能设备
5. `get_system_overview` - 获取整个智能家居系统的概览

## 架构设计

### 技术栈
- **LangChain**: 提供AI代理框架和工具集成
- **A2A (Agent-to-Agent)**: 代理间通信协议
- **LangGraph**: 构建复杂的代理工作流
- **DeepSeek**: 作为底层大语言模型

### 系统架构
```
用户请求 → ConductorAgent → 工具选择 → 代理通信 → 响应返回
                ↓
         [空调代理] [空气净化器代理] [其他代理...]
```

## 安装和运行

### 环境要求
- Python 3.8+
- 依赖包见 `requirements.txt`

### 启动服务
```bash
# 启动总管理代理服务器 (端口 12002)
python server.py --host localhost --port 12002

# 或者使用默认配置
python server.py
```

### 测试功能
```bash
# 运行测试脚本
python test_conductor.py
```

## 使用示例

### 1. 查看可用代理
```
用户: "查看所有可用的代理服务"
代理: 调用 list_available_agents 工具
响应: 返回所有注册的代理列表
```

### 2. 控制设备
```
用户: "把空调温度调到25度"
代理: 调用 control_device 工具
参数: device_type="air_conditioner", action="set_temperature", parameters={"temperature": 25}
```

### 3. 系统状态查询
```
用户: "检查系统状态"
代理: 调用 get_system_overview 工具
响应: 返回系统整体状态和所有代理信息
```

## 配置说明

### 代理注册
在 `tools.py` 中的 `REGISTERED_AGENTS` 字典中注册新的代理：

```python
REGISTERED_AGENTS = {
    "air_conditioner": {
        "name": "空调代理",
        "url": "http://localhost:12000",
        "description": "控制家庭空调系统",
        "capabilities": ["温度控制", "电源管理", "模式切换"]
    },
    "air_cleaner": {
        "name": "空气净化器代理", 
        "url": "http://localhost:12001",
        "description": "控制空气净化器设备",
        "capabilities": ["空气质量监测", "净化模式控制", "滤网状态"]
    }
}
```

### 端口配置
- 总管理代理: `12002`
- 空调代理: `12000`
- 空气净化器代理: `12001`

## API 接口

### A2A 协议支持
总管理代理完全支持A2A协议，可以：
- 接收A2A格式的请求
- 返回标准化的响应
- 支持流式响应
- 处理任务状态更新

### 支持的输入模式
- `text/plain` - 纯文本输入
- 支持中文自然语言指令

## 扩展开发

### 添加新工具
1. 在 `tools.py` 中定义新的工具函数
2. 使用 `@tool` 装饰器标记
3. 在 `main.py` 中添加到工具列表
4. 更新系统提示词

### 添加新代理
1. 在 `REGISTERED_AGENTS` 中注册新代理
2. 实现代理间的通信逻辑
3. 更新相关工具函数

## 故障排除

### 常见问题
1. **代理连接失败**: 检查代理服务是否正常运行
2. **工具调用错误**: 验证工具参数格式
3. **响应超时**: 检查网络连接和代理响应时间

### 日志查看
```bash
# 查看详细日志
python server.py --host localhost --port 12002
```

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 许可证

本项目采用 MIT 许可证。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目 Issues
- 邮箱: [your-email@example.com]

---

**注意**: 这是一个演示项目，在生产环境中使用前请进行充分测试和安全评估。
