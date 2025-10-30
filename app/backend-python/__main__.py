"""
主入口点 - 用于 `uv run .` 或 `python -m moss_ai_backend` 启动服务
FastAPI 后端服务 - Moss AI 智能家居系统
提供前端与 Conductor Agent 之间的通信桥梁
"""

import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# 确保当前目录在 Python 路径中
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from api.chat import router as chat_router
from api.config import router as config_router
from api.xiaomi_auth import router as xiaomi_router
from api.auth import router as auth_router
from config import settings
from database import init_database, DatabaseConnectionError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 Moss AI 后端服务启动中...")
    logger.info(f"📍 Conductor Agent URL: {settings.CONDUCTOR_AGENT_URL}")
    logger.info(f"🔧 环境: {settings.ENVIRONMENT}")
    
    # 初始化数据库连接（严格模式：连接失败则退出）
    try:
        init_database(strict_mode=True)
        logger.info("✅ 数据库初始化成功")
    except DatabaseConnectionError as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        logger.error("⚠️  请确保:")
        logger.error("   1. StarRocks 数据库已启动")
        logger.error("   2. 已执行数据库初始化脚本: data/init_config.sql 和 data/ai_config.sql")
        logger.error("   3. config.yaml 中的数据库连接配置正确")
        logger.error("⚠️  服务启动失败，进程即将退出...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 未知错误: {e}")
        logger.error("⚠️  服务启动失败，进程即将退出...")
        sys.exit(1)
    
    yield
    logger.info("👋 Moss AI 后端服务关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Moss AI Backend API",
    description="智能家居系统后端服务，连接前端与 AI Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
app.include_router(config_router, prefix="/api/v1/config", tags=["Config"])
app.include_router(xiaomi_router, prefix="/api/v1/xiaomi", tags=["Xiaomi Auth"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])


@app.get("/")
async def root():
    """根路径 - API 信息"""
    return {
        "name": "Moss AI Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"全局异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "message": str(exc),
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "__main__:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        http="h11",  # 使用 h11 避免 httptools 问题
    )
