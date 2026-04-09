import yaml
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import pymysql
from pymysql.cursors import DictCursor
import os
from pathlib import Path

# 全局数据库连接实例
db = None

class DatabaseConnectionError(Exception):
    """数据库连接错误"""
    
    def __init__(self, original_error: Exception = None):
        """
        初始化数据库连接错误
        
        Args:
            original_error: 原始异常对象（可选）
        """
        self.original_error = original_error
        
        # 构建错误消息
        message = "请检查数据库连接"
        if original_error:
            message = f"{message}: {original_error}"
        
        super().__init__(message)
        self.message = message

# 数据库连接管理类
class DatabaseConnection:
    # 初始化数据库连接
    def __init__(self, config_path: str = "../../config.yaml", strict_mode: bool = True):
        self.strict_mode = strict_mode
        self._connection = None
        self.config = self._load_config(config_path)
        # 获取数据库类型，默认为 starrocks
        self.db_type = self.config.get('database', {}).get('type', 'starrocks')
        # 根据类型选择对应的配置
        self.db_config = self.config.get('database', {}).get(self.db_type, {})
    
    # 加载配置文件
    def _load_config(self, config_path: str) -> dict:
        try:
            # 处理绝对路径
            if os.path.isabs(config_path):
                yaml_path = Path(config_path)
            else:
                # 尝试相对于当前文件的路径
                current_dir = Path(__file__).parent
                yaml_path = (current_dir / config_path).resolve()
                
                # 如果找不到，向上查找项目根目录的 config.yaml
                if not yaml_path.exists():
                    # 从当前目录开始向上查找
                    search_dir = Path.cwd()
                    for _ in range(5):  # 最多向上查找5层
                        candidate = search_dir / "config.yaml"
                        if candidate.exists():
                            yaml_path = candidate
                            break
                        search_dir = search_dir.parent
            
            if not yaml_path.exists():
                raise FileNotFoundError(f"配置文件未找到: {config_path}")
            
            with open(yaml_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            if self.strict_mode:
                raise DatabaseConnectionError(e)
            raise
    
    # 获取数据库连接
    def get_connection(self):
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
                connect_timeout=5
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