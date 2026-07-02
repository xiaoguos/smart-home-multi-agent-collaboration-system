import logging
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

current_dir = Path(__file__).parent
load_dotenv(current_dir / ".env")

if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from api.chat import router as chat_router
from api.config import router as config_router
from api.xiaomi_auth import router as xiaomi_router
from api.dida_auth import router as dida_router
from api.auth import router as auth_router
from api.conversation import router as conversation_router
from api.device_operations import router as device_operations_router
from api.knowledge_base import router as knowledge_base_router
import database
from database import init_database, DatabaseConnectionError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_database(strict_mode=True)
    except DatabaseConnectionError as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 未知错误,请联系开发者解决: {e}")
        sys.exit(1)

    yield
    logger.info("👋 Smart Home Multi-Agent Collaboration System 后端服务关闭")


app = FastAPI(
    title="Smart Home Multi-Agent Collaboration System Backend API",
    description="智能家居系统后端服务",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
    or ["http://localhost:1420", "http://127.0.0.1:1420", "http://localhost:3000", "http://127.0.0.1:3000", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
app.include_router(conversation_router, prefix="/api/v1", tags=["Conversation"])
app.include_router(config_router, prefix="/api/v1/config", tags=["Config"])
app.include_router(xiaomi_router, prefix="/api/v1/xiaomi", tags=["Xiaomi Auth"])
app.include_router(dida_router, prefix="/api/v1/dida", tags=["Dida Auth"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(device_operations_router, prefix="/api/v1", tags=["Device Operations"])
app.include_router(knowledge_base_router, prefix="/api/v1", tags=["Knowledge Base"])


@app.get("/")
async def root():
    return {
        "name": "Smart Home Multi-Agent Collaboration System Backend API",
        "version": "1.0.0",
        "status": "运行中",
        "warning": "请浏览正确路径,不要浏览错误路径",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"全局异常,请联系开发者解决: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "message": str(exc),
        }
    )
