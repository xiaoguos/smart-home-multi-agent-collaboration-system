from langchain_core.tools import tool
import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库文件路径 - 使用绝对路径，放在当前模块目录下
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_behavior.db")

def init_database():
    """初始化数据库表结构"""
    try:
        conn = sqlite3.connect(DB_PATH)
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
        logger.info("数据库初始化完成")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


@tool("save_device_operation_log", description="保存设备操作日志到数据库")
def save_device_operation_log(
    user_id: str,
    device_type: str,
    device_name: str,
    action: str,
    parameters: str = None,
    success: bool = True,
    response: str = None
):
    """保存设备操作日志到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO device_operations 
            (user_id, device_type, device_name, action, parameters, success, response)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, device_type, device_name, action, parameters, success, response))
        
        conn.commit()
        conn.close()
        
        return json.dumps({
            "message": "设备操作日志保存成功",
            "user_id": user_id,
            "device_type": device_type,
            "action": action,
            "timestamp": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"保存操作日志失败: {e}")
        return json.dumps({
            "error": str(e),
            "message": "保存操作日志失败"
        }, indent=2, ensure_ascii=False)


@tool("analyze_user_habits", description="分析用户使用习惯")
def analyze_user_habits(user_id: str, days: int = 30):
    """分析指定用户在最近N天的使用习惯"""
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # 查询最近N天的操作记录
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        query = '''
            SELECT device_type, action, parameters, timestamp, success
            FROM device_operations 
            WHERE user_id = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        '''
        
        df = pd.read_sql_query(query, conn, params=(user_id, start_date))
        conn.close()
        
        if df.empty:
            return json.dumps({
                "message": f"用户 {user_id} 在最近 {days} 天内没有操作记录",
                "user_id": user_id,
                "analysis_period": f"{days} days",
                "habits": []
            }, indent=2, ensure_ascii=False)
        
        # 分析使用习惯
        habits = []
        
        # 1. 设备使用频率分析
        device_usage = df['device_type'].value_counts().to_dict()
        habits.append({
            "type": "device_usage_frequency",
            "data": device_usage,
            "description": "设备使用频率统计"
        })
        
        # 2. 操作时间模式分析
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        time_pattern = df['hour'].value_counts().sort_index().to_dict()
        habits.append({
            "type": "time_pattern",
            "data": time_pattern,
            "description": "操作时间分布模式"
        })
        
        # 3. 常用操作分析
        action_usage = df['action'].value_counts().to_dict()
        habits.append({
            "type": "common_actions",
            "data": action_usage,
            "description": "常用操作统计"
        })
        
        # 4. 成功率分析
        success_rate = df['success'].mean()
        habits.append({
            "type": "success_rate",
            "data": {"success_rate": success_rate},
            "description": "操作成功率"
        })
        
        # 5. 参数偏好分析（针对空调温度设置）
        if 'air_conditioner' in device_usage:
            ac_operations = df[df['device_type'] == 'air_conditioner']
            temp_settings = []
            for _, row in ac_operations.iterrows():
                if row['action'] == 'set_temperature' and row['parameters']:
                    try:
                        params = json.loads(row['parameters'])
                        if 'temperature' in params:
                            temp_settings.append(params['temperature'])
                    except:
                        continue
            
            if temp_settings:
                avg_temp = sum(temp_settings) / len(temp_settings)
                habits.append({
                    "type": "temperature_preference",
                    "data": {
                        "average_temperature": round(avg_temp, 1),
                        "temperature_range": [min(temp_settings), max(temp_settings)],
                        "sample_count": len(temp_settings)
                    },
                    "description": "温度偏好分析"
                })
        
        return json.dumps({
            "message": f"用户 {user_id} 习惯分析完成",
            "user_id": user_id,
            "analysis_period": f"{days} days",
            "total_operations": len(df),
            "habits": habits,
            "generated_at": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"分析用户习惯失败: {e}")
        return json.dumps({
            "error": str(e),
            "message": "分析用户习惯失败"
        }, indent=2, ensure_ascii=False)


@tool("get_user_operation_history", description="获取用户操作历史记录")
def get_user_operation_history(user_id: str, device_type: str = None, limit: int = 50):
    """获取用户的操作历史记录"""
    try:
        conn = sqlite3.connect(DB_PATH)
        
        if device_type:
            query = '''
                SELECT * FROM device_operations 
                WHERE user_id = ? AND device_type = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            '''
            df = pd.read_sql_query(query, conn, params=(user_id, device_type, limit))
        else:
            query = '''
                SELECT * FROM device_operations 
                WHERE user_id = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            '''
            df = pd.read_sql_query(query, conn, params=(user_id, limit))
        
        conn.close()
        
        if df.empty:
            return json.dumps({
                "message": f"用户 {user_id} 没有找到操作记录",
                "user_id": user_id,
                "device_type": device_type,
                "operations": []
            }, indent=2, ensure_ascii=False)
        
        # 转换DataFrame为字典列表
        operations = df.to_dict('records')
        
        return json.dumps({
            "message": f"获取用户 {user_id} 操作历史成功",
            "user_id": user_id,
            "device_type": device_type,
            "total_count": len(operations),
            "operations": operations
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取操作历史失败: {e}")
        return json.dumps({
            "error": str(e),
            "message": "获取操作历史失败"
        }, indent=2, ensure_ascii=False)


@tool("predict_user_preference", description="预测用户偏好设置")
def predict_user_preference(user_id: str, device_type: str, context: str = None):
    """基于历史数据预测用户偏好设置"""
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # 获取用户最近的操作记录
        query = '''
            SELECT action, parameters, timestamp
            FROM device_operations 
            WHERE user_id = ? AND device_type = ? AND success = 1
            ORDER BY timestamp DESC 
            LIMIT 100
        '''
        
        df = pd.read_sql_query(query, conn, params=(user_id, device_type))
        conn.close()
        
        if df.empty:
            return json.dumps({
                "message": f"用户 {user_id} 没有 {device_type} 的操作记录",
                "user_id": user_id,
                "device_type": device_type,
                "prediction": None
            }, indent=2, ensure_ascii=False)
        
        predictions = {}
        
        if device_type == 'air_conditioner':
            # 分析温度设置偏好
            temp_settings = []
            for _, row in df.iterrows():
                if row['action'] == 'set_temperature' and row['parameters']:
                    try:
                        params = json.loads(row['parameters'])
                        if 'temperature' in params:
                            temp_settings.append(params['temperature'])
                    except:
                        continue
            
            if temp_settings:
                # 计算最常用的温度
                from collections import Counter
                temp_counter = Counter(temp_settings)
                most_common_temp = temp_counter.most_common(1)[0][0]
                avg_temp = sum(temp_settings) / len(temp_settings)
                
                predictions['temperature'] = {
                    "most_common": most_common_temp,
                    "average": round(avg_temp, 1),
                    "confidence": min(len(temp_settings) / 10, 1.0)  # 基于样本数量的置信度
                }
        
        # 分析操作时间偏好
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        time_preference = df['hour'].mode().iloc[0] if not df['hour'].mode().empty else None
        
        if time_preference is not None:
            predictions['preferred_time'] = {
                "hour": int(time_preference),
                "description": f"用户通常在 {time_preference}:00 左右操作设备"
            }
        
        return json.dumps({
            "message": f"用户 {user_id} 偏好预测完成",
            "user_id": user_id,
            "device_type": device_type,
            "context": context,
            "predictions": predictions,
            "confidence": "基于历史数据分析",
            "generated_at": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"预测用户偏好失败: {e}")
        return json.dumps({
            "error": str(e),
            "message": "预测用户偏好失败"
        }, indent=2, ensure_ascii=False)


@tool("get_system_analytics", description="获取系统整体分析数据")
def get_system_analytics(days: int = 7):
    """获取系统整体的分析数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 总体统计
        query = '''
            SELECT 
                COUNT(*) as total_operations,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(DISTINCT device_type) as device_types,
                AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM device_operations 
            WHERE timestamp >= ?
        '''
        
        stats = pd.read_sql_query(query, conn, params=(start_date,)).iloc[0]
        
        # 设备使用统计
        device_stats_query = '''
            SELECT device_type, COUNT(*) as usage_count
            FROM device_operations 
            WHERE timestamp >= ?
            GROUP BY device_type
            ORDER BY usage_count DESC
        '''
        
        device_stats = pd.read_sql_query(device_stats_query, conn, params=(start_date,))
        
        # 用户活跃度统计
        user_stats_query = '''
            SELECT user_id, COUNT(*) as operation_count
            FROM device_operations 
            WHERE timestamp >= ?
            GROUP BY user_id
            ORDER BY operation_count DESC
        '''
        
        user_stats = pd.read_sql_query(user_stats_query, conn, params=(start_date,))
        
        conn.close()
        
        return json.dumps({
            "message": f"系统分析数据获取成功",
            "analysis_period": f"{days} days",
            "summary": {
                "total_operations": int(stats['total_operations']),
                "unique_users": int(stats['unique_users']),
                "device_types": int(stats['device_types']),
                "success_rate": round(stats['success_rate'], 3)
            },
            "device_usage": device_stats.to_dict('records'),
            "user_activity": user_stats.to_dict('records'),
            "generated_at": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取系统分析数据失败: {e}")
        return json.dumps({
            "error": str(e),
            "message": "获取系统分析数据失败"
        }, indent=2, ensure_ascii=False)


# 初始化数据库
init_database()
