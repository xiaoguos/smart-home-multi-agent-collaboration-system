"""
配置文件 - 从统一的 config.yaml 读取配置
"""

import yaml
import os
from typing import List
from pathlib import Path


class Settings:
    """应用配置 - 从 config.yaml 加载"""
    
    def __init__(self):
        """从 config.yaml 加载配置"""
        self.config = self._load_config()
        
        # 从配置文件读取
        backend_config = self.config.get('backend', {}).get('python', {})
        
        # 服务配置
        self.HOST: str = backend_config.get('host', '0.0.0.0')
        self.PORT: int = backend_config.get('port', 3000)
        self.ENVIRONMENT: str = backend_config.get('environment', 'development')
        self.DEBUG: bool = backend_config.get('debug', True)
        
        # Conductor Agent 配置
        self.CONDUCTOR_AGENT_URL: str = backend_config.get('conductor_agent_url', 'http://localhost:12000')
        self.CONDUCTOR_TIMEOUT: int = backend_config.get('conductor_timeout', 120)
        
        # CORS 配置
        self.CORS_ORIGINS: List[str] = backend_config.get('cors_origins', [
            "http://localhost:1420",
            "http://127.0.0.1:1420",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "tauri://localhost",
        ])
    
    def _load_config(self) -> dict:
        """加载 YAML 配置文件"""
        # 查找 config.yaml
        config_path = self._find_config_file()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ 加载配置文件失败: {e}")
            return {}
    
    def _find_config_file(self) -> Path:
        """自动查找 config.yaml"""
        # 从当前文件向上查找
        current = Path(__file__).parent
        
        for _ in range(5):  # 最多向上查找5层
            config_path = current / "config.yaml"
            if config_path.exists():
                return config_path
            current = current.parent
        
        # 如果没找到，返回默认路径
        return Path(__file__).parent.parent.parent / "config.yaml"


settings = Settings()

