"""
配置文件
"""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 服务配置
    HOST: str = "127.0.0.1"
    PORT: int = 2100
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Conductor Agent 配置
    CONDUCTOR_AGENT_URL: str = "http://localhost:12000"
    CONDUCTOR_TIMEOUT: int = 120  # 秒
    
    # CORS 配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:1420",  # Vite 前端
        "http://127.0.0.1:1420",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "tauri://localhost",  # Tauri 应用
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

