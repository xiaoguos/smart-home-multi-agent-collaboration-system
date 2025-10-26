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
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """数据库连接错误"""
    pass


class DatabaseConnection:
    """数据库连接管理类"""
    
    def __init__(self, config_path: str = "../../config.yaml", strict_mode: bool = True):
        """
        初始化数据库连接
        
        Args:
            config_path: 配置文件路径
            strict_mode: 严格模式，如果为True则数据库连接失败时抛出异常
        """
        self.strict_mode = strict_mode
        self._connection = None
        self.config = self._load_config(config_path)
        self.db_config = self.config.get('database', {}).get('starrocks', {})
    
    def _load_config(self, config_path: str) -> dict:
        """加载YAML配置文件"""
        try:
            # 处理相对路径
            if not os.path.isabs(config_path):
                current_dir = Path(__file__).parent
                yaml_path = (current_dir / config_path).resolve()
            else:
                yaml_path = Path(config_path)
            
            with open(yaml_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            error_msg = f"加载配置文件失败: {e}"
            logger.error(error_msg)
            if self.strict_mode:
                raise DatabaseConnectionError(error_msg) from e
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
                autocommit=True,
                connect_timeout=5  # 5秒连接超时
            )
            return connection
        except Exception as e:
            error_msg = f"数据库连接失败: {e}"
            logger.error(error_msg)
            if self.strict_mode:
                raise DatabaseConnectionError(error_msg) from e
            raise
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            连接是否成功
            
        Raises:
            DatabaseConnectionError: 在严格模式下连接失败时抛出
        """
        try:
            logger.info("🔍 测试数据库连接...")
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            connection.close()
            
            if result:
                logger.info("✅ 数据库连接测试成功")
                return True
            else:
                error_msg = "数据库连接测试失败: 无法执行测试查询"
                logger.error(f"❌ {error_msg}")
                if self.strict_mode:
                    raise DatabaseConnectionError(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"数据库连接测试失败: {e}"
            logger.error(f"❌ {error_msg}")
            if self.strict_mode:
                raise DatabaseConnectionError(error_msg) from e
            return False
    
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


# 全局数据库连接实例（默认启用严格模式）
db = None


def init_database(strict_mode: bool = True) -> DatabaseConnection:
    """
    初始化数据库连接
    
    Args:
        strict_mode: 严格模式，如果为True则数据库连接失败时抛出异常
        
    Returns:
        数据库连接实例
    """
    global db
    if db is None:
        db = DatabaseConnection(strict_mode=strict_mode)
        # 测试连接
        db.test_connection()
    return db


# 便捷函数
def query(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    """执行查询"""
    if db is None:
        raise DatabaseConnectionError("数据库未初始化，请先调用 init_database()")
    return db.execute_query(sql, params)


def update(sql: str, params: tuple = None) -> int:
    """执行更新"""
    if db is None:
        raise DatabaseConnectionError("数据库未初始化，请先调用 init_database()")
    return db.execute_update(sql, params)


def insert(sql: str, params: tuple = None) -> int:
    """执行插入"""
    if db is None:
        raise DatabaseConnectionError("数据库未初始化，请先调用 init_database()")
    return db.execute_update(sql, params)

