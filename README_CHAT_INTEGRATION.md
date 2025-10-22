# Moss AI 聊天集成文档

## 架构说明

本项目实现了一个三层架构的智能家居对话系统：

```
前端 (React + Ant Design X)  ←→  后端 (Cangjie)  ←→  Conductor Agent (Python + A2A SDK)
     Chat.tsx                      chat.cj                 main.py
     Port: 5173                    Port: 2100              Port: 12000
```

## 功能特点

- **前端**：使用 Ant Design X 提供美观的聊天界面
- **后端**：Cangjie 语言实现的中间层，处理 HTTP 请求
- **AI Agent**：基于 LangChain 和 DeepSeek 的智能家居控制助手

## 启动步骤

### 1. 安装依赖

#### Python 依赖（Conductor Agent）
```bash
pip install -r requirements.txt
```

#### Node.js 依赖（前端）
```bash
cd app
pnpm install
# 或 npm install
```

### 2. 启动服务

按照以下顺序启动各个服务：

#### 步骤 1：启动 Conductor Agent (A2A Server)
```bash
cd agents/conductor_agent
python main.py --host localhost --port 12000
```

服务将运行在 `http://localhost:12000`

#### 步骤 2：启动 Cangjie 后端服务器

首先构建后端：
```bash
cd app/backend
cjpm build
```

然后运行：
```bash
# Windows
dist\release\bin\main.exe

# Linux/Mac
./dist/release/bin/main
```

服务将运行在 `http://127.0.0.1:2100`

#### 步骤 3：启动前端开发服务器
```bash
cd app
pnpm dev
# 或 npm run dev
```

前端将运行在 `http://localhost:5173`（或其他端口，根据 Vite 配置）

### 3. 测试系统

1. 打开浏览器访问前端地址
2. 在聊天界面输入消息，例如：
   - "查看所有可用代理"
   - "开启空调"
   - "关闭空气净化器"
   - "获取系统概览"
   - "我要睡觉了"（智能场景）

## API 接口说明

### Conductor Agent API (Port: 12000) - A2A 协议

#### 1. 获取 Agent 卡片
```
GET /
或
GET /agent_card
```

#### 2. 发送消息（A2A 协议）
```
POST /send_message
Content-Type: application/json

{
  "context_id": "会话ID",
  "role": "user",
  "parts": [
    {
      "kind": "text",
      "text": "用户消息"
    }
  ],
  "message_id": "消息ID"
}

响应：A2A 标准响应格式
```

### 后端 API (Port: 2100)

#### 聊天接口
```
POST /api/chat
Content-Type: application/json

{
  "query": "用户消息",
  "context_id": "会话ID"
}

响应：
{
  "is_task_complete": true,
  "require_user_input": false,
  "content": "AI 回复内容"
}
```

## 技术栈

### 前端
- React 18
- TypeScript
- Ant Design X（聊天组件）
- Axios（HTTP 客户端）
- Vite（构建工具）

### 后端
- Cangjie 语言
- HTTP Server（stdx.net.http）
- JSON 处理（stdx.encoding.json）

### AI Agent
- Python 3.x
- LangChain（AI 框架）
- DeepSeek Chat（大语言模型）
- A2A SDK（Agent-to-Agent 协议）
- Uvicorn（ASGI 服务器）

## 文件结构

```
moss-ai/
├── agents/
│   └── conductor_agent/
│       ├── agent.py              # Agent 核心逻辑
│       ├── executor.py           # A2A 执行器
│       ├── main.py               # A2A Server 入口
│       └── tools.py              # 工具函数
├── app/
│   ├── backend/
│   │   └── src/
│   │       ├── main.cj           # 主入口
│   │       └── server/
│   │           ├── default.cj    # 服务器配置
│   │           └── api/
│   │               └── chat.cj   # 聊天 API
│   └── src/
│       └── pages/
│           └── Chat.tsx          # 聊天界面
└── requirements.txt              # Python 依赖
```

## 故障排查

### 1. 前端无法连接后端
- 检查后端服务是否运行在 `http://127.0.0.1:2100`
- 检查浏览器控制台的网络请求错误

### 2. 后端无法连接 Conductor Agent
- 检查 Conductor Agent 是否运行在 `http://localhost:12000`
- 使用 `curl http://localhost:12000/` 测试连接
- 查看后端日志确认连接状态

### 3. AI 响应错误
- 检查 DeepSeek API 密钥是否有效
- 查看 Conductor Agent 日志了解详细错误信息

### 4. CORS 错误
- 检查 Cangjie 后端是否设置了正确的 CORS 头
- A2A SDK 默认支持跨域，通常不会有此问题

## 开发建议

1. **日志记录**：三个层次都有日志输出，便于调试
2. **错误处理**：各层都有完善的错误处理和友好的错误提示
3. **会话管理**：使用 context_id 维护对话上下文
4. **扩展性**：可以轻松添加更多的 Agent 工具和功能

## 下一步

- [ ] 实现流式响应（Server-Sent Events）
- [ ] 添加用户认证
- [ ] 实现对话历史持久化
- [ ] 优化错误处理和重试机制
- [ ] 添加更多智能家居设备支持

