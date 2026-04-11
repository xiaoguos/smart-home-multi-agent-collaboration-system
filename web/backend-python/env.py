"""从 web/backend-python/.env 读取环境变量，首次 import 时执行 load_dotenv。"""

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_FILE)

_DEFAULT_CORS: list[str] = [
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "tauri://localhost",
]


def _bool_env(key: str, default: bool) -> bool:
    v = os.getenv(key)
    if v is None or not str(v).strip():
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _int_env(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None or not str(v).strip():
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return list(_DEFAULT_CORS)
    parts = [x.strip() for x in raw.split(",") if x.strip()]
    return parts if parts else list(_DEFAULT_CORS)


HOST = os.getenv("HOST", "0.0.0.0")
PORT = _int_env("PORT", 3000)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = _bool_env("DEBUG", True)

CONDUCTOR_AGENT_URL = os.getenv("CONDUCTOR_AGENT_URL", "http://localhost:12000")
CONDUCTOR_TIMEOUT = _int_env("CONDUCTOR_TIMEOUT", 120)

CORS_ORIGINS = _cors_origins()

DATABASE_TYPE = os.getenv("DATABASE_TYPE", "starrocks")
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = _int_env("DATABASE_PORT", 9030)
DATABASE_USER = os.getenv("DATABASE_USER", "root")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "smart_home")
DATABASE_CHARSET = os.getenv("DATABASE_CHARSET", "utf8mb4")
