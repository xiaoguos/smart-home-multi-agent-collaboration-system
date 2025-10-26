"""
数据库连接模块
支持 StarRocks 数据库连接
"""

import yaml
import logging
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """数据库连接管理类"""
    
    def __init__(self, config_path: str = "../../config.yaml"):
        """
        初始化数据库连接
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.db_config = self.config.get('database', {}).get('starrocks', {})
        self._connection = None
    
    def _load_config(self, config_path: str) -> dict:
        """加载YAML配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def get_connection(self):
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
                autocommit=True
            )
            return connection
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    @contextmanager
    def get_cursor(self):
        """获取数据库游标（上下文管理器）"""
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
            connection.close()
    
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行查询SQL
        
        Args:
            sql: SQL语句
            params: 参数元组
            
        Returns:
            查询结果列表
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    def execute_update(self, sql: str, params: tuple = None) -> int:
        """
        执行更新SQL（INSERT/UPDATE/DELETE）
        
        Args:
            sql: SQL语句
            params: 参数元组
            
        Returns:
            影响的行数
        """
        with self.get_cursor() as cursor:
            affected = cursor.execute(sql, params)
            return affected
    
    def execute_many(self, sql: str, params_list: List[tuple]) -> int:
        """
        批量执行SQL
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            
        Returns:
            影响的总行数
        """
        with self.get_cursor() as cursor:
            affected = cursor.executemany(sql, params_list)
            return affected


# 全局数据库连接实例
db = DatabaseConnection()


# 便捷函数
def query(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    """执行查询"""
    return db.execute_query(sql, params)


def update(sql: str, params: tuple = None) -> int:
    """执行更新"""
    return db.execute_update(sql, params)


def insert(sql: str, params: tuple = None) -> int:
    """执行插入"""
    return db.execute_update(sql, params)

