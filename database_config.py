"""
数据库配置模块
支持多种数据库类型：SQLite, MySQL, PostgreSQL, StarRocks
"""

import yaml
import os
import logging
from typing import Dict, Any, Optional
import sqlite3
import pymysql
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """数据库配置管理类"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """初始化数据库配置"""
        self.config_path = config_path
        self.config = self._load_config()
        self.db_type = self.config.get('database', {}).get('type', 'sqlite')
        self.engine = None
        self.session_factory = None
        
    def _load_config(self) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"配置文件 {self.config_path} 不存在，使用默认配置")
            return self._get_default_config()
        except yaml.YAMLError as e:
            logger.error(f"配置文件解析错误: {e}")
            raise
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'database': {
                'type': 'sqlite',
                'sqlite': {'path': 'user_behavior.db'}
            }
        }
    
    def get_connection_string(self) -> str:
        """获取数据库连接字符串"""
        db_config = self.config.get('database', {})
        
        if self.db_type == 'sqlite':
            sqlite_config = db_config.get('sqlite', {})
            path = sqlite_config.get('path', 'user_behavior.db')
            return f"sqlite:///{path}"
        
        elif self.db_type == 'starrocks':
            starrocks_config = db_config.get('starrocks', {})
            host = starrocks_config.get('host', 'localhost')
            port = starrocks_config.get('port', 9030)
            user = starrocks_config.get('user', 'root')
            password = starrocks_config.get('password', 'password')
            database = starrocks_config.get('database', 'smart_home')
            charset = starrocks_config.get('charset', 'utf8mb4')
            
            # StarRocks使用MySQL协议
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"
        
        elif self.db_type == 'mysql':
            mysql_config = db_config.get('mysql', {})
            host = mysql_config.get('host', 'localhost')
            port = mysql_config.get('port', 3306)
            user = mysql_config.get('user', 'root')
            password = mysql_config.get('password', 'password')
            database = mysql_config.get('database', 'smart_home')
            charset = mysql_config.get('charset', 'utf8mb4')
            
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"
        
        elif self.db_type == 'postgresql':
            pg_config = db_config.get('postgresql', {})
            host = pg_config.get('host', 'localhost')
            port = pg_config.get('port', 5432)
            user = pg_config.get('user', 'postgres')
            password = pg_config.get('password', 'password')
            database = pg_config.get('database', 'smart_home')
            
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")
    
    def get_engine(self):
        """获取SQLAlchemy引擎"""
        if self.engine is None:
            connection_string = self.get_connection_string()
            
            # 获取连接池配置
            db_config = self.config.get('database', {})
            pool_size = db_config.get('pool_size', 10)
            max_overflow = db_config.get('max_overflow', 20)
            pool_timeout = db_config.get('pool_timeout', 30)
            pool_recycle = db_config.get('pool_recycle', 3600)
            
            self.engine = create_engine(
                connection_string,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=pool_recycle,
                echo=False
            )
            
            # 创建会话工厂
            self.session_factory = sessionmaker(bind=self.engine)
        
        return self.engine
    
    @contextmanager
    def get_session(self):
        """获取数据库会话上下文管理器"""
        if self.session_factory is None:
            self.get_engine()
        
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_raw_connection(self):
        """获取原始数据库连接（用于直接SQL操作）"""
        if self.db_type == 'sqlite':
            sqlite_config = self.config.get('database', {}).get('sqlite', {})
            path = sqlite_config.get('path', 'user_behavior.db')
            return sqlite3.connect(path)
        
        elif self.db_type in ['starrocks', 'mysql']:
            config = self.config.get('database', {}).get(self.db_type, {})
            return pymysql.connect(
                host=config.get('host', 'localhost'),
                port=config.get('port', 3306 if self.db_type == 'mysql' else 9030),
                user=config.get('user', 'root'),
                password=config.get('password', 'password'),
                database=config.get('database', 'smart_home'),
                charset=config.get('charset', 'utf8mb4')
            )
        
        elif self.db_type == 'postgresql':
            config = self.config.get('database', {}).get('postgresql', {})
            return psycopg2.connect(
                host=config.get('host', 'localhost'),
                port=config.get('port', 5432),
                user=config.get('user', 'postgres'),
                password=config.get('password', 'password'),
                database=config.get('database', 'smart_home')
            )
        
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")
    
    def init_database(self):
        """初始化数据库表结构"""
        try:
            if self.db_type == 'sqlite':
                self._init_sqlite_tables()
            else:
                self._init_mysql_tables()
            logger.info("数据库表初始化完成")
        except Exception as e:
            logger.error(f"数据库表初始化失败: {e}")
            raise
    
    def _init_sqlite_tables(self):
        """初始化SQLite表结构"""
        conn = self.get_raw_connection()
        cursor = conn.cursor()
        
        # 创建设备操作日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                device_type TEXT NOT NULL,
                device_name TEXT NOT NULL,
                action TEXT NOT NULL,
                parameters TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT TRUE,
                response TEXT
            )
        ''')
        
        # 创建用户习惯分析表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                habit_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # 创建设备使用统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                device_type TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                last_used DATETIME,
                preferred_settings TEXT,
                usage_frequency TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_mysql_tables(self):
        """初始化MySQL/StarRocks表结构"""
        conn = self.get_raw_connection()
        cursor = conn.cursor()
        
        # 创建设备操作日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_operations (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                device_type VARCHAR(100) NOT NULL,
                device_name VARCHAR(255) NOT NULL,
                action VARCHAR(100) NOT NULL,
                parameters TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT TRUE,
                response TEXT,
                INDEX idx_user_id (user_id),
                INDEX idx_device_type (device_type),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # 创建用户习惯分析表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_habits (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                habit_type VARCHAR(100) NOT NULL,
                pattern_data TEXT NOT NULL,
                confidence_score DECIMAL(5,2) DEFAULT 0.00,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                INDEX idx_user_id (user_id),
                INDEX idx_habit_type (habit_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # 创建设备使用统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_usage_stats (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                device_type VARCHAR(100) NOT NULL,
                usage_count INT DEFAULT 0,
                last_used DATETIME,
                preferred_settings TEXT,
                usage_frequency VARCHAR(50),
                INDEX idx_user_id (user_id),
                INDEX idx_device_type (device_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        conn.commit()
        conn.close()
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            if self.db_type == 'sqlite':
                conn = self.get_raw_connection()
                conn.execute("SELECT 1")
                conn.close()
            else:
                with self.get_session() as session:
                    session.execute(text("SELECT 1"))
            
            logger.info(f"数据库连接测试成功: {self.db_type}")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False


# 全局数据库配置实例
db_config = DatabaseConfig()


def get_db_config() -> DatabaseConfig:
    """获取数据库配置实例"""
    return db_config


def get_connection():
    """获取数据库连接"""
    return db_config.get_raw_connection()


@contextmanager
def get_session():
    """获取数据库会话"""
    with db_config.get_session() as session:
        yield session
