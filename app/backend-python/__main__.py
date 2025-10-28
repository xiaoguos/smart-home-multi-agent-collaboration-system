"""
主入口点 - 用于 `uv run .` 或 `python -m moss_ai_backend` 启动服务
"""

import sys
from pathlib import Path

# 确保当前目录在 Python 路径中
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import uvicorn
from config import settings


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )


