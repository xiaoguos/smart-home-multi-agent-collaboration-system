"""
Agent配置加载器
从 config.yaml 和 StarRocks 数据库中加载Agent配置和AI模型配置
支持统一配置管理
"""

import sys
import os
import yaml
import pymysql
from pymysql.cursors import DictCursor
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """数据库连接错误"""
    pass


class ConfigLoadError(Exception):
    """配置加载错误"""
    pass


class AgentConfigLoader:
    """Agent配置加载器类 - 支持从 config.yaml 和数据库加载配置"""
    
    def __init__(self, config_path: str = None, strict_mode: bool = True):
        """
        初始化配置加载器
        
        Args:
            config_path: YAML配置文件路径，如果为None则自动查找
            strict_mode: 严格模式，如果为True则数据库连接失败时抛出异常
        """
        # 自动查找 config.yaml
        if config_path is None:
            config_path = self._find_config_file()
        
        self.config = self._load_yaml_config(config_path)
        self.db_config = self.config.get('database', {}).get('starrocks', {})
        self.agents_config = self.config.get('agents', {})
        self.backend_config = self.config.get('backend', {})
        self.logging_config = self.config.get('logging', {})
        self.strict_mode = strict_mode
        self._connection_tested = False
    
    def _find_config_file(self) -> str:
        """自动查找 config.yaml 文件"""
        # 1. 从当前文件所在目录向上查找
        current_dir = Path(__file__).parent
        
        # 向上查找最多3层
        for _ in range(3):
            config_path = current_dir / "config.yaml"
            if config_path.exists():
                logger.info(f"找到配置文件: {config_path}")
                return str(config_path)
            current_dir = current_dir.parent
        
        # 2. 默认路径（项目根目录）
        default_path = Path(__file__).parent.parent / "config.yaml"
        if default_path.exists():
            return str(default_path)
        
        raise FileNotFoundError("未找到 config.yaml 配置文件")
    
    def _load_yaml_config(self, config_path: str) -> dict:
        """加载YAML配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _get_db_connection(self):
        """获取数据库连接"""
        try:
            connection = pymysql.connect(
                host=self.db_config.get('host', 'localhost'),
                port=self.db_config.get('port', 9030),
                user=self.db_config.get('user', 'root'),
                password=self.db_config.get('password', ''),
                database=self.db_config.get('database', 'smart_home'),
                charset=self.db_config.get('charset', 'utf8mb4'),
                cursorclass=DictCursor,
                connect_timeout=5  # 5秒连接超时
            )
            self._connection_tested = True
            return connection
        except Exception as e:
            error_msg = f"数据库连接失败: {e}"
            logger.error(error_msg)
            if self.strict_mode:
                raise DatabaseConnectionError(error_msg) from e
            raise
    
    def get_default_ai_model_config(self) -> Optional[Dict[str, Any]]:
        """
        获取默认的AI模型配置
        
        Returns:
            AI模型配置字典，包含 model, api_key, api_base, temperature, max_tokens
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            sql = """
                SELECT model_name, provider, api_key, api_base, temperature, max_tokens
                FROM ai_model_config
                WHERE is_default = TRUE AND is_active = TRUE
                LIMIT 1
            """
            cursor.execute(sql)
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                logger.info(f"成功从数据库加载AI模型配置: {result['model_name']}")
                return {
                    'model': result['model_name'],
                    'api_key': result['api_key'],
                    'api_base': result['api_base'],
                    'temperature': float(result['temperature']),
                    'max_tokens': result['max_tokens']
                }
            else:
                error_msg = "数据库中未找到默认AI模型配置"
                logger.error(error_msg)
                if self.strict_mode:
                    raise ConfigLoadError(error_msg)
                return None
        except (DatabaseConnectionError, ConfigLoadError):
            raise
        except Exception as e:
            error_msg = f"获取AI模型配置失败: {e}"
            logger.error(error_msg)
            if self.strict_mode:
                raise ConfigLoadError(error_msg) from e
            return None
    
    def get_agent_config(self, agent_code: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent配置
        
        Args:
            agent_code: Agent代码标识
            
        Returns:
            Agent配置字典
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            sql = """
                SELECT agent_code, agent_name, host, port, description, is_enabled
                FROM agent_config
                WHERE agent_code = %s AND is_enabled = TRUE
                LIMIT 1
            """
            cursor.execute(sql, (agent_code,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return result
        except Exception as e:
            logger.error(f"获取Agent配置失败: {e}")
            return None
    
    def get_agent_prompt(self, agent_code: str) -> Optional[str]:
        """
        获取Agent的系统提示词
        
        Args:
            agent_code: Agent代码标识
            
        Returns:
            系统提示词文本
            
        Raises:
            ConfigLoadError: 严格模式下配置加载失败时抛出
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            sql = """
                SELECT prompt_text
                FROM agent_prompt
                WHERE agent_code = %s AND is_active = TRUE
                ORDER BY id DESC
                LIMIT 1
            """
            cursor.execute(sql, (agent_code,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                logger.info(f"成功从数据库加载 {agent_code} 的系统提示词")
                return result['prompt_text']
            else:
                error_msg = f"数据库中未找到 {agent_code} 的系统提示词"
                logger.error(error_msg)
                if self.strict_mode:
                    raise ConfigLoadError(error_msg)
                return None
        except (DatabaseConnectionError, ConfigLoadError):
            raise
        except Exception as e:
            error_msg = f"获取Agent提示词失败: {e}"
            logger.error(error_msg)
            if self.strict_mode:
                raise ConfigLoadError(error_msg) from e
            return None
    
    def get_device_config(self, device_code: str) -> Optional[Dict[str, Any]]:
        """
        获取设备配置
        
        Args:
            device_code: 设备代码
            
        Returns:
            设备配置字典
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            sql = """
                SELECT device_code, device_name, device_type, agent_code, 
                       ip_address, token, model, extra_config, is_active
                FROM device_config
                WHERE device_code = %s AND is_active = TRUE
                LIMIT 1
            """
            cursor.execute(sql, (device_code,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return result
        except Exception as e:
            logger.error(f"获取设备配置失败: {e}")
            return None
    
    def get_xiaomi_account(self) -> Optional[Dict[str, Any]]:
        """
        获取默认小米账号配置
        
        Returns:
            小米账号配置字典
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            sql = """
                SELECT username, password, region
                FROM xiaomi_account
                WHERE is_default = TRUE AND is_active = TRUE
                LIMIT 1
            """
            cursor.execute(sql)
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return result
        except Exception as e:
            logger.error(f"获取小米账号配置失败: {e}")
            return None
    
    # ==================== 新增：统一配置读取方法 ====================
    
    def get_agent_host_port(self, agent_name: str) -> tuple[str, int]:
        """
        从 config.yaml 获取 Agent 的 host 和 port
        
        Args:
            agent_name: Agent 名称 (如 'conductor', 'air_conditioner')
            
        Returns:
            (host, port) 元组
        """
        agent_cfg = self.agents_config.get(agent_name, {})
        host = agent_cfg.get('host', 'localhost')
        port = agent_cfg.get('port', 12000)
        return host, port
    
    def get_backend_config_value(self, key: str, default: Any = None) -> Any:
        """
        获取后端配置值
        
        Args:
            key: 配置键，支持点号分隔的路径 (如 'python.host')
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.backend_config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.logging_config
    
    def get_all_agents_config(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Agent 的配置"""
        return self.agents_config


# 全局配置加载器实例
_config_loader = None


def get_config_loader(strict_mode: bool = True) -> AgentConfigLoader:
    """
    获取全局配置加载器实例
    
    Args:
        strict_mode: 严格模式，如果为True则数据库连接失败时抛出异常
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = AgentConfigLoader(strict_mode=strict_mode)
    return _config_loader

