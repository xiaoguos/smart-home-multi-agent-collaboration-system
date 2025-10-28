# Moss AI Backend

Moss AI 智能家居系统的 Python 后端服务，提供前端与 Conductor Agent 之间的通信桥梁。

## 快速开始

### 安装依赖

使用 uv（推荐）：
```bash
uv sync
```

或使用 pip：
```bash
pip install -r requirements.txt
```

### 启动服务

使用 uv：
```bash
uv run .
```

或直接使用 Python：
```bash
python -m moss_ai_backend
```

或运行 main.py：
```bash
python main.py
```

### 开发模式

服务默认运行在 `http://0.0.0.0:3000`，可以通过修改 `config.yaml` 中的配置来更改。

## 项目结构

```
backend-python/
├── api/              # API 路由
│   ├── chat.py      # 聊天相关接口
│   └── config.py    # 配置相关接口
├── models/          # 数据模型
│   └── chat.py      # 聊天模型
├── services/        # 服务层
│   ├── conductor_service.py  # Conductor Agent 服务
│   └── config_service.py     # 配置服务
├── config.py        # 配置管理
├── database.py      # 数据库连接
├── main.py          # FastAPI 应用
├── __init__.py      # 包初始化
├── __main__.py      # 入口点
├── pyproject.toml   # 项目配置
└── requirements.txt # 依赖列表
```

## API 文档

启动服务后，访问以下地址查看 API 文档：
- Swagger UI: http://localhost:3000/docs
- ReDoc: http://localhost:3000/redoc

## 配置

所有配置通过项目根目录的 `config.yaml` 文件管理。主要配置项：

```yaml
backend:
  python:
    host: "0.0.0.0"
    port: 3000
    environment: "development"
    debug: true
    conductor_agent_url: "http://localhost:12000"
    conductor_timeout: 120
```

## 依赖

- FastAPI: Web 框架
- Uvicorn: ASGI 服务器
- SQLAlchemy: ORM
- PyMySQL: MySQL 驱动
- PyYAML: YAML 解析
- httpx: HTTP 客户端

