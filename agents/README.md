# 智能家居代理系统

## 系统概述

这是一个基于LangChain和A2A架构的智能家居管理系统，包含多个专业代理，通过总管理代理进行统一协调。

## 系统架构

```
用户请求
    ↓
总管理代理 (Conductor Agent)
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│   空调代理      │   空气净化器代理  │   数据挖掘代理   │
│ (AC Agent)      │ (Air Cleaner)   │ (Data Mining)   │
│ Port: 12000     │ Port: 12001     │ Port: 12003     │
└─────────────────┴─────────────────┴─────────────────┘
    ↓
数据库 (SQLite)
user_behavior.db
```

## 代理功能

### 🎯 总管理代理 (Conductor Agent)
- **端口**: 12002
- **功能**: 
  - 协调所有智能设备代理
  - 提供统一的控制接口
  - 自动记录所有操作日志
  - 分析用户行为数据
  - 提供个性化建议

### ❄️ 空调代理 (Air Conditioner Agent)
- **端口**: 12000
- **功能**:
  - 控制空调温度设置
  - 管理电源开关
  - 模式切换（制冷/制热/送风）
  - 实时状态查询

### 🌬️ 空气净化器代理 (Air Cleaner Agent)
- **端口**: 12001
- **功能**:
  - 空气质量监测
  - 净化模式控制
  - 滤网状态管理
  - 自动净化调节

### 📊 数据挖掘代理 (Data Mining Agent)
- **端口**: 12003
- **功能**:
  - 分析用户使用习惯
  - 预测用户偏好设置
  - 生成使用统计报告
  - 提供个性化建议

## 核心特性

### 🔄 自动日志记录
- 所有设备操作自动保存到数据库
- 记录用户ID、设备类型、操作、参数、时间戳
- 支持操作成功/失败状态跟踪

### 📈 用户行为分析
- 基于历史数据挖掘使用模式
- 分析设备使用频率和时间分布
- 识别温度偏好和操作习惯
- 生成个性化使用建议

### 🤖 智能协调
- 总管理代理统一调度所有子代理
- 支持代理间通信和协作
- 提供统一的API接口
- 实时状态监控

## 数据库设计

### 设备操作日志表 (device_operations)
```sql
CREATE TABLE device_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    device_type TEXT NOT NULL,
    device_name TEXT NOT NULL,
    action TEXT NOT NULL,
    parameters TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    response TEXT
);
```

### 用户习惯分析表 (user_habits)
```sql
CREATE TABLE user_habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    habit_type TEXT NOT NULL,
    pattern_data TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

### 设备使用统计表 (device_usage_stats)
```sql
CREATE TABLE device_usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    device_type TEXT NOT NULL,
    usage_count INTEGER DEFAULT 0,
    last_used DATETIME,
    preferred_settings TEXT,
    usage_frequency TEXT
);
```

## 快速开始

### 1. 启动所有代理服务

```bash
# 启动空调代理
cd agents/air_conditioner_agent
python server.py --port 12000

# 启动空气净化器代理
cd agents/air_cleaner_agent
python server.py --port 12001

# 启动数据挖掘代理
cd agents/dw_agent
python server.py --port 12003

# 启动总管理代理
cd agents/conductor_agent
python server.py --port 12002
```

### 2. 运行集成测试

```bash
cd agents
python test_integrated_system.py
```

### 3. 使用示例

#### 通过总管理代理控制设备
```python
# 设置空调温度
POST http://localhost:12002/
{
    "message": "把空调温度调到25度"
}

# 分析使用习惯
POST http://localhost:12002/
{
    "message": "分析我的使用习惯"
}
```

#### 直接调用数据挖掘代理
```python
# 分析用户行为
POST http://localhost:12003/
{
    "message": "分析用户default_user在最近30天的使用习惯"
}
```

## 使用场景

### 🏠 智能家居控制
- "把空调调到26度"
- "开启空气净化器"
- "检查所有设备状态"

### 📊 行为分析
- "分析我的使用习惯"
- "我通常在什么时候使用空调？"
- "根据我的习惯推荐最佳温度设置"

### 🎯 个性化服务
- "获取个性化建议"
- "预测我今晚的空调设置偏好"
- "生成我的使用报告"

## 技术栈

- **LangChain**: AI代理框架
- **LangGraph**: 复杂工作流管理
- **A2A**: 代理间通信协议
- **SQLite**: 数据存储
- **DeepSeek**: 大语言模型
- **FastAPI/Starlette**: Web服务框架

## 扩展开发

### 添加新设备代理
1. 在 `agents/` 目录下创建新的代理目录
2. 实现 `main.py`, `tools.py`, `agent_executor.py`, `server.py`
3. 在总管理代理的 `REGISTERED_AGENTS` 中注册
4. 更新数据库表结构（如需要）

### 添加新的分析功能
1. 在数据挖掘代理的 `tools.py` 中添加新工具
2. 更新 `main.py` 中的工具列表
3. 在总管理代理中集成新功能

## 配置说明

### 环境变量
```bash
# DeepSeek API配置
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_API_BASE=https://api.deepseek.com

# 数据库配置
DB_PATH=user_behavior.db
```

### 端口配置
- 总管理代理: 12002
- 空调代理: 12000
- 空气净化器代理: 12001
- 数据挖掘代理: 12003

## 故障排除

### 常见问题
1. **代理启动失败**: 检查端口是否被占用
2. **数据库连接错误**: 确保有写入权限
3. **API调用失败**: 检查DeepSeek API密钥和网络连接

### 日志查看
```bash
# 查看代理日志
tail -f agent.log

# 查看数据库
sqlite3 user_behavior.db
.tables
SELECT * FROM device_operations LIMIT 10;
```

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 许可证

MIT License

---

**注意**: 这是一个演示项目，在生产环境中使用前请进行充分测试和安全评估。
