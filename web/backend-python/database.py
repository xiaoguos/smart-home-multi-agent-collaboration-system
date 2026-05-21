from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor

import os

# 全局数据库连接实例
db = None

class DatabaseConnectionError(Exception):
    """数据库连接错误"""
    
    def __init__(self, original_error: Exception = None):
        self.original_error = original_error
        message = "请检查数据库连接"
        if original_error:
            message = f"{message}: {original_error}"
        super().__init__(message)
        self.message = message

# 数据库连接管理类
class DatabaseConnection:
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self._connection = None
        self.db_type = os.getenv("DATABASE_TYPE", "mysql")
        self.db_config = {
            "host": os.getenv("DATABASE_HOST", "localhost"),
            "port": int(os.getenv("DATABASE_PORT", "3306")),
            "user": os.getenv("DATABASE_USER", "root"),
            "password": os.getenv("DATABASE_PASSWORD", ""),
            "database": os.getenv("DATABASE_NAME", "moss_ai"),
            "charset": os.getenv("DATABASE_CHARSET", "utf8mb4"),
        }
    
    # 获取数据库连接
    def get_connection(self):
        try:
            connection = pymysql.connect(
                host=self.db_config.get("host", "localhost"),
                port=self.db_config.get("port", 9030),
                user=self.db_config.get("user", "root"),
                password=self.db_config.get("password", ""),
                database=self.db_config.get("database", "moss_ai"),
                charset=self.db_config.get("charset", "utf8mb4"),
                cursorclass=DictCursor,
                autocommit=True,
                connect_timeout=5,
                read_timeout=15,
                write_timeout=15,
            )
            return connection
        except Exception as e:
            if self.strict_mode:
                raise DatabaseConnectionError(e)
            raise
    
    # 测试数据库连接
    def test_connection(self) -> bool:
        # 测试数据库连接
        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            connection.close()
            
            if result:
                return True
            else:
                if self.strict_mode:
                    raise DatabaseConnectionError()
                return False
                
        except Exception as e:
            if self.strict_mode:
                raise DatabaseConnectionError(e)
            return False
    
    # 获取数据库游标（上下文管理器）
    @contextmanager
    def get_cursor(self):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
            connection.close()
    
    # 执行查询SQL
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    # 执行更新SQL（INSERT/UPDATE/DELETE）
    def execute_update(self, sql: str, params: tuple = None) -> int:
        with self.get_cursor() as cursor:
            affected = cursor.execute(sql, params)
            return affected
    
    # 批量执行SQL
    def execute_many(self, sql: str, params_list: List[tuple]) -> int:
        with self.get_cursor() as cursor:
            affected = cursor.executemany(sql, params_list)
            return affected

def init_database(strict_mode: bool = True) -> DatabaseConnection:
    global db
    if db is None:
        db = DatabaseConnection(strict_mode=strict_mode)
        db.test_connection()
    return db

# 查询
def query(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    if db is None:
        raise DatabaseConnectionError()
    return db.execute_query(sql, params)

# 更新
def update(sql: str, params: tuple = None) -> int:
    if db is None:
        raise DatabaseConnectionError()
    return db.execute_update(sql, params)

# 插入
def insert(sql: str, params: tuple = None) -> int:
    if db is None:
        raise DatabaseConnectionError()
    return db.execute_update(sql, params)

# 获取数据库类型
def get_db_type() -> str:
    if db is None:
        raise DatabaseConnectionError()
    return db.db_type
