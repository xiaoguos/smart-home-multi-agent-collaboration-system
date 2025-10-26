# 配置迁移至数据库指南

## 📋 概述

本次更新将原本散落在 `config.yaml` 和各个 Agent 代码中的配置统一迁移到 StarRocks 数据库中进行管理，实现了配置的集中化、动态化管理。

## ✨ 主要变更

### 1. 数据库初始化脚本

包含两个独立的 SQL 文件：

**文件1**: `data/init_config.sql`
- 创建核心配置表（5个）：
  - `system_config` - 系统配置表
  - `agent_config` - Agent配置表
  - `agent_prompt` - Agent系统提示词表
  - `device_config` - 设备配置表
  - `xiaomi_account` - 小米账号配置表
- 插入基础配置数据

**文件2**: `data/ai_config.sql`（完全独立）
- 创建 `ai_model_config` 表
- 插入 AI 模型配置（DeepSeek、OpenAI 等）
- 可单独执行，不依赖其他脚本

### 2. 精简配置文件

**文件**: `config.yaml`

现在只保留数据库连接配置：
- StarRocks 连接信息
- 连接池配置
- 开发模式配置

所有其他配置已迁移到数据库。

### 3. 后端配置管理系统

#### 新增文件

1. **`app/backend-python/database.py`**
   - 数据库连接管理类
   - 提供查询、更新等便捷方法

2. **`app/backend-python/services/config_service.py`**
   - 配置管理服务类
   - 提供各类配置的 CRUD 操作

3. **`app/backend-python/api/config.py`**
   - 配置管理 REST API 接口
   - 支持 AI 模型、Agent、设备、小米账号等配置管理

#### 更新文件

- **`app/backend-python/requirements.txt`**
  - 新增 `PyMySQL`、`SQLAlchemy`、`PyYAML` 依赖

- **`app/backend-python/main.py`**
  - 注册配置管理路由 `/api/v1/config/*`

### 4. Agent 配置加载器

**文件**: `agents/config_loader.py`

- 统一的配置加载器类
- 从数据库读取 AI 模型配置、系统提示词等
- 提供全局单例访问

### 5. 更新所有 Agent

修改了以下 Agent，使其从数据库读取配置：
- `agents/conductor_agent/agent.py`
- `agents/air_conditioner_agent/agent.py`
- `agents/bedside_lamp_agent/agent.py`
- `agents/air_cleaner_agent/agent.py`

所有 Agent 现在会：
1. 从数据库加载 AI 模型配置（API Key、Base URL 等）
2. 从数据库加载系统提示词
3. 如果数据库连接失败，使用默认配置作为备用

### 6. 前端配置管理界面

#### 新增文件

**`app/src/api/config.ts`**
- 配置管理 API 接口封装
- TypeScript 类型定义

#### 更新文件

**`app/src/pages/Setting.tsx`**

完全重构的配置管理页面，包含四个Tab：

1. **AI 模型配置**
   - 查看、编辑、新增 AI 模型
   - 管理 API Key、温度参数等

2. **小米账号配置**
   - 管理小米账号和区域设置
   - 支持多账号配置

3. **Agent 配置**
   - 查看和编辑 Agent 端口、描述等
   - 启用/禁用 Agent

4. **设备配置**
   - 管理智能设备配置
   - 设备 IP、Token、型号等信息

## 🚀 部署步骤

### 1. 初始化数据库

```bash
# 方式1：使用 mysql 命令行（推荐）
mysql -h localhost -P 9030 -u root -p < data/init_config.sql
mysql -h localhost -P 9030 -u root -p < data/ai_config.sql

# 方式2：连接到 StarRocks 后执行
mysql -h localhost -P 9030 -u root -p
# 然后在 mysql 命令行中执行：
source data/init_config.sql
source data/ai_config.sql
```

**注意**：
- 数据文件统一位于项目根目录的 `data/` 文件夹
- `init_config.sql` - 创建核心表结构（5个表）和基础配置数据
- `ai_config.sql` - 创建 AI 模型配置表并插入数据（完全独立，可单独执行）
- 两个脚本完全独立，执行顺序无关

### 2. 安装 Python 依赖

```bash
cd app/backend-python
pip install -r requirements.txt
```

### 3. 启动后端服务

```bash
cd app/backend-python
python main.py
```

服务将在 `http://localhost:3000` 启动

### 4. 启动各个 Agent

```bash
# 使用现有的启动脚本
.\script\start_agents.ps1
```

### 5. 启动前端

```bash
cd app
npm install  # 如果需要
npm run dev
```

## 📝 API 接口文档

### AI 模型管理

- `GET /api/v1/config/ai-models` - 获取所有 AI 模型
- `GET /api/v1/config/ai-models/default` - 获取默认模型
- `GET /api/v1/config/ai-models/{id}` - 获取指定模型
- `PUT /api/v1/config/ai-models/{id}` - 更新模型配置
- `POST /api/v1/config/ai-models` - 创建新模型

### Agent 管理

- `GET /api/v1/config/agents` - 获取所有 Agent
- `GET /api/v1/config/agents/{code}` - 获取指定 Agent
- `PUT /api/v1/config/agents/{id}` - 更新 Agent 配置
- `GET /api/v1/config/agents/{code}/prompt` - 获取 Agent 提示词
- `PUT /api/v1/config/agents/{code}/prompt` - 更新 Agent 提示词

### 设备管理

- `GET /api/v1/config/devices` - 获取所有设备
- `GET /api/v1/config/devices/{code}` - 获取指定设备
- `PUT /api/v1/config/devices/{id}` - 更新设备配置
- `POST /api/v1/config/devices` - 创建新设备

### 小米账号管理

- `GET /api/v1/config/xiaomi-accounts` - 获取所有账号
- `GET /api/v1/config/xiaomi-accounts/default` - 获取默认账号
- `PUT /api/v1/config/xiaomi-accounts/{id}` - 更新账号配置
- `POST /api/v1/config/xiaomi-accounts` - 创建新账号

### 系统配置管理

- `GET /api/v1/config/system-config` - 获取系统配置列表
- `GET /api/v1/config/system-config/{key}` - 获取指定配置项
- `PUT /api/v1/config/system-config/{key}` - 更新配置项

## 🔧 配置管理

### 通过前端界面管理

1. 访问系统设置页面
2. 选择相应的配置 Tab（AI 模型、小米账号、Agent、设备）
3. 点击"编辑"或"新增"按钮
4. 修改配置并保存

### 通过 API 管理

使用 HTTP 客户端（如 Postman、curl）直接调用 API：

```bash
# 示例：获取所有 AI 模型
curl http://localhost:3000/api/v1/config/ai-models

# 示例：更新 AI 模型配置
curl -X PUT http://localhost:3000/api/v1/config/ai-models/1 \
  -H "Content-Type: application/json" \
  -d '{"api_key": "new-api-key"}'
```

### 通过数据库直接管理

```sql
-- 示例：更新 AI 模型的 API Key
UPDATE ai_model_config 
SET api_key = 'new-api-key', updated_at = NOW() 
WHERE id = 1;

-- 示例：查看所有 Agent 配置
SELECT * FROM agent_config WHERE is_enabled = TRUE;
```

## 🎯 优势

1. **集中管理** - 所有配置统一在数据库中管理
2. **动态更新** - 修改配置后重启 Agent 即可生效，无需修改代码
3. **版本控制** - Agent 提示词支持版本管理
4. **可视化界面** - 通过前端界面直观地管理配置
5. **安全性** - 敏感信息（如 API Key）集中存储在数据库中
6. **扩展性** - 易于添加新的配置项和配置类型

## ⚠️ 注意事项

1. **备份数据库** - 在初始化前请备份现有数据
2. **API Key 安全** - 建议对数据库中的 API Key 进行加密存储
3. **重启 Agent** - 修改配置后需要重启相应的 Agent 才能生效
4. **数据库连接** - 确保 `config.yaml` 中的数据库连接配置正确

## 🔄 回滚方案

如果需要回滚到旧版本：

1. 保留旧的 `config.yaml` 文件备份
2. 恢复各个 Agent 的原始代码（从 Git 历史）
3. 删除新增的数据库表（如果需要）

## 📞 支持

如有问题，请查看：
- 数据库日志
- 后端服务日志
- Agent 日志

或联系开发团队。

