# Data Mining Agent - 用户行为数据挖掘与场景分析

## 概述

Data Mining Agent 是 Moss AI 智能家居系统中的数据挖掘与分析模块，负责从 StarRocks 数据库中挖掘用户的设备使用习惯，使用高斯混合模型(GMM)进行场景聚类分析，为 Conductor Agent 提供个性化的设备操作推荐。

## 主要功能

### 1. 用户行为数据挖掘
- 从 StarRocks 数据库读取设备操作历史记录
- 支持按用户ID和时间范围查询
- 自动过滤失败的操作记录

### 2. GMM 场景聚类分析
- 使用高斯混合模型对用户行为进行无监督聚类
- 自动识别用户的使用场景（2-5个场景）
- 提取时间特征：小时、分钟、星期几、时段等
- 提取设备特征：设备类型编码

### 3. 场景特征分析
- 分析每个场景的时间分布特征
- 统计每个场景中的设备操作频次
- 识别最常见的操作和参数
- 生成场景描述和命名

### 4. 智能场景匹配
- 根据用户查询匹配最相关的场景
- 支持时间关键词匹配（早上、晚上、睡觉等）
- 支持设备关键词匹配（空调、灯、净化器等）
- 综合考虑场景出现频率

### 5. 个性化推荐
- 基于历史数据生成设备操作建议
- 包含具体的设备类型、操作和参数
- 提供推荐置信度（基于数据量）

## 技术架构

### 核心算法：GMM (Gaussian Mixture Model)
- **无监督学习**：无需人工标注，自动发现场景模式
- **概率建模**：每个场景被建模为一个高斯分布
- **软聚类**：支持场景之间的模糊边界
- **自适应聚类数**：根据数据量动态调整场景数量

### 数据流程
```
用户查询 → 数据库查询 → 特征提取 → GMM聚类 → 场景分析 → 场景匹配 → 生成推荐
```

### 特征工程
**时间特征**：
- hour: 小时 (0-23)
- minute: 分钟 (0-59)
- day_of_week: 星期几 (0-6)
- is_weekend: 是否周末 (0/1)
- is_morning/afternoon/evening/night: 时段标记

**设备特征**：
- is_ac: 是否空调
- is_cleaner: 是否净化器
- is_lamp: 是否灯具

## API 接口

### 工具函数

#### 1. query_user_scene_habits
查询用户场景习惯，执行 GMM 聚类分析

**参数**：
- `user_query` (str): 用户的场景描述或查询
- `system_user_id` (int): 系统用户ID，默认1
- `days` (int): 查询最近N天的数据，默认30

**返回**：JSON格式的分析结果
```json
{
  "status": "success",
  "message": "基于最近30天的50条记录，识别出3个使用场景",
  "user_query": "我要睡觉了",
  "total_operations": 50,
  "identified_scenes": 3,
  "matched_scene": {
    "scene_id": 2,
    "scene_name": "场景3_夜晚",
    "time_period": "夜晚",
    "avg_hour": 22.5,
    "occurrence_count": 18,
    "device_actions": {...},
    "description": "在夜晚时段，用户通常会：..."
  },
  "recommendation": {
    "scene_name": "场景3_夜晚",
    "time_period": "夜晚",
    "confidence": "高",
    "suggested_actions": [
      {
        "device_type": "air_conditioner",
        "device_name": "空调",
        "action": "设置温度",
        "frequency": 15,
        "parameters": {"temperature": 26}
      }
    ]
  },
  "all_scenes": [...]
}
```

**数据不足时的响应**：
```json
{
  "status": "insufficient_data",
  "message": "历史数据不足（仅5条记录），建议使用通用最佳实践",
  "user_query": "我要睡觉了",
  "data_count": 5,
  "recommendation": null
}
```

#### 2. get_data_mining_status
获取数据挖掘Agent的状态和统计信息

**返回**：
```json
{
  "status": "online",
  "message": "数据挖掘Agent运行正常",
  "database_status": "connected",
  "statistics": {
    "total_operations": 1250,
    "total_users": 5,
    "device_breakdown": {
      "air_conditioner": 450,
      "air_cleaner": 380,
      "bedside_lamp": 420
    }
  },
  "capabilities": [
    "GMM场景聚类分析",
    "用户习惯挖掘",
    "个性化场景推荐",
    "历史行为分析"
  ]
}
```

## 与 Conductor Agent 的协作

### 调用流程
1. **用户查询** → Conductor Agent
2. Conductor Agent 调用 `query_data_mining_agent` 工具
3. Data Mining Agent 分析历史数据并返回推荐
4. Conductor Agent 根据推荐执行设备控制

### 保底机制
当 Data Mining Agent 返回 `insufficient_data` 状态时：
- Conductor Agent 启用保底方案
- 调用 `search_baidu_ai` 获取通用最佳实践
- 告知用户："随着使用次数增多，我会学习您的个人习惯"

## A2A 协议适配

### Agent Card 配置
- **Name**: Data Mining Agent
- **Description**: 智能家居用户行为数据挖掘与场景分析专家
- **Skills**: 
  - ID: `analyze_user_behavior`
  - Name: User Behavior Analysis & Scene Mining
- **Capabilities**:
  - Push Notifications: ❌
  - Streaming: ❌
  - State History: ❌

### 支持的内容类型
- Input: `text`, `text/plain`
- Output: `text`, `text/plain`

## 数据库依赖

### 表结构
使用 StarRocks 数据库的 `device_operations` 表：
```sql
CREATE TABLE device_operations (
    id BIGINT,
    system_user_id BIGINT,
    created_at DATETIME,
    context_id VARCHAR(100),
    device_type VARCHAR(50),
    device_name VARCHAR(100),
    action VARCHAR(100),
    parameters STRING,  -- JSON格式
    success BOOLEAN,
    response STRING,
    error_message STRING,
    execution_time INT
)
```

## 部署和运行

### 1. 安装依赖
```bash
cd agents/data_mining_agent
uv sync
```

### 2. 配置数据库
确保 `config.yaml` 中的 StarRocks 配置正确：
```yaml
database:
  type: starrocks
  starrocks:
    host: localhost
    port: 9030
    user: root
    password: ""
    database: smart_home
```

### 3. 添加系统提示词到数据库
```sql
INSERT INTO agent_prompt (id, agent_code, prompt_text, version, is_active, created_at, updated_at) VALUES
(5, 'data_mining', '...', 'v1.0', TRUE, NOW(), NOW());
```

### 4. 启动服务
```bash
# 使用默认配置（从数据库读取）
uv run .

# 或指定主机和端口
uv run . --host localhost --port 12004
```

### 5. 验证服务
```bash
curl http://localhost:12004/
```

## 配置说明

### Agent 配置（数据库）
在 `agent_config` 表中配置：
```sql
INSERT INTO agent_config VALUES
(5, 'data_mining', 'Data Mining Agent', 'localhost', 12004, 
 '用户行为数据挖掘代理', TRUE, NOW(), NOW());
```

### Conductor Agent 集成
在 `conductor_agent/tools.py` 的 `REGISTERED_AGENTS` 中添加：
```python
"data_mining": {
    "name": "数据挖掘代理",
    "url": "http://localhost:12004",
    "description": "分析用户行为数据",
    "capabilities": ["习惯分析", "偏好预测", "历史查询", "统计分析"]
}
```

## 使用示例

### 示例1：睡觉场景分析
**输入**：
```
query_user_scene_habits("我要睡觉了", system_user_id=1, days=30)
```

**输出**：
```json
{
  "matched_scene": {
    "scene_name": "场景3_夜晚",
    "time_period": "夜晚",
    "description": "在夜晚时段，用户通常会：\n- 对空调执行「设置温度26°C」\n- 对床头灯执行「设置睡眠模式」\n- 对空气净化器执行「设置睡眠模式」"
  },
  "recommendation": {
    "suggested_actions": [
      {"device_type": "air_conditioner", "action": "设置温度", "parameters": {"temperature": 26}},
      {"device_type": "bedside_lamp", "action": "设置睡眠模式"},
      {"device_type": "air_cleaner", "action": "设置睡眠模式"}
    ]
  }
}
```

### 示例2：数据不足
**输入**：
```
query_user_scene_habits("打开空调", system_user_id=999, days=30)
```

**输出**：
```json
{
  "status": "insufficient_data",
  "message": "历史数据不足（仅3条记录），建议使用通用最佳实践",
  "recommendation": null
}
```

## 性能优化

### 1. 数据库查询优化
- 使用索引：`system_user_id`, `created_at`
- 限制查询时间范围（默认30天）
- 只查询成功的操作记录

### 2. GMM 聚类优化
- 动态调整聚类数：`min(5, len(X) // 5)`
- 特征标准化：使用 StandardScaler
- 设置最大迭代次数：100

### 3. 缓存策略
- 可考虑缓存同一用户的分析结果
- 设置缓存过期时间（如1小时）

## 故障处理

### 数据库连接失败
- 检查 StarRocks 是否运行
- 验证 config.yaml 配置
- 检查网络连接

### 数据不足
- 正常情况，返回 `insufficient_data`
- Conductor Agent 会启用保底方案

### GMM 聚类失败
- 检查样本数量是否足够（至少2个）
- 检查特征是否正确提取
- 查看日志了解详细错误

## 日志说明

### 关键日志
- `✅ 数据库配置加载成功`
- `📊 查询到 N 条设备操作记录`
- `✅ GMM聚类完成: N个样本被分为M个场景`
- `⚠️ 历史数据不足`
- `❌ 数据库连接失败`

## 未来扩展

### 1. 更多聚类算法
- DBSCAN：密度聚类
- K-Means：快速聚类
- 层次聚类：场景层级关系

### 2. 时间序列分析
- 预测用户下一步操作
- 异常行为检测

### 3. 多用户协同过滤
- 学习相似用户的习惯
- 冷启动问题解决

### 4. 实时学习
- 在线更新聚类模型
- 增量学习

## 许可证

MIT License

## 联系方式

Moss AI Team

