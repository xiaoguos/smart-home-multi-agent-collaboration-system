"""
FastAPI 后端服务 - Moss AI 智能家居系统
提供前端与 Conductor Agent 之间的通信桥梁
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.chat import router as chat_router
from config import settings

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
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )

