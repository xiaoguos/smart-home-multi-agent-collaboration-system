from langchain_core.tools import tool
import json
import sqlite3
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 导入数据库配置
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from database_config import get_db_config

# 获取数据库配置
db_config = get_db_config()


class SceneRecommendationArgs(BaseModel):
    scene_type: str = Field(..., description="场景类型，如：睡觉、起床、离家、回家、工作、休息等")
    user_id: str = Field(default="default_user", description="用户ID")
    context: Dict[str, Any] = Field(default_factory=dict, description="场景上下文信息，如当前时间、环境数据等")


@tool("get_scene_recommendations", args_schema=SceneRecommendationArgs, 
     description="根据场景类型和用户历史习惯，提供设备控制建议。例如：睡觉场景会建议空调温度、床头灯亮度等")
def get_scene_recommendations(scene_type: str, user_id: str = "default_user", context: Dict[str, Any] = None) -> str:
    """
    根据场景类型分析用户历史习惯，提供设备控制建议
    
    Args:
        scene_type: 场景类型（睡觉、起床、离家、回家等）
        user_id: 用户ID
        context: 场景上下文信息
        
    Returns:
        JSON格式的建议列表
    """
    try:
        if context is None:
            context = {}
            
        conn = db_config.get_raw_connection()
        cursor = conn.cursor()
        
        # 确保表存在
        _ensure_tables_exist(cursor)
        
        current_hour = datetime.now().hour
        current_month = datetime.now().month
        
        recommendations = []
        
        # 根据不同场景类型提供建议
        if scene_type in ["睡觉", "睡眠", "准备睡觉", "要睡觉了"]:
            recommendations = _analyze_sleep_scene(cursor, user_id, current_hour, current_month)
        elif scene_type in ["起床", "早晨", "起来了"]:
            recommendations = _analyze_wakeup_scene(cursor, user_id, current_hour, current_month)
        elif scene_type in ["离家", "出门", "离开"]:
            recommendations = _analyze_leaving_scene(cursor, user_id, current_hour)
        elif scene_type in ["回家", "到家", "回来了"]:
            recommendations = _analyze_arriving_scene(cursor, user_id, current_hour, current_month)
        elif scene_type in ["工作", "办公", "学习"]:
            recommendations = _analyze_work_scene(cursor, user_id, current_hour, current_month)
        else:
            # 通用场景分析
            recommendations = _analyze_general_scene(cursor, user_id, scene_type, current_hour)
        
        conn.close()
        
        result = {
            "scene_type": scene_type,
            "user_id": user_id,
            "current_time": datetime.now().isoformat(),
            "recommendations": recommendations,
            "has_historical_data": len(recommendations) > 0,
            "message": f"根据您的历史使用习惯，为{scene_type}场景提供以下建议" if recommendations else f"暂无{scene_type}场景的历史数据，建议使用默认设置"
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取场景建议失败: {e}", exc_info=True)
        return json.dumps({
            "error": str(e),
            "scene_type": scene_type,
            "message": "获取场景建议失败，建议使用默认设置"
        }, indent=2, ensure_ascii=False)


def _ensure_tables_exist(cursor):
    """确保必要的表存在"""
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            scene_type TEXT NOT NULL,
            device_type TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            recommended_parameters TEXT,
            confidence_score REAL DEFAULT 0.0,
            sample_count INTEGER DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')


def _analyze_sleep_scene(cursor, user_id: str, current_hour: int, current_month: int) -> List[Dict]:
    """分析睡觉场景的历史习惯"""
    recommendations = []
    
    # 查询晚上时段（20:00-02:00）的历史操作
    cursor.execute('''
        SELECT device_type, action, parameters, 
               strftime('%H', timestamp) as hour,
               COUNT(*) as frequency
        FROM device_operations
        WHERE user_id = ? 
        AND success = 1
        AND (CAST(strftime('%H', timestamp) AS INTEGER) >= 20 OR CAST(strftime('%H', timestamp) AS INTEGER) <= 2)
        GROUP BY device_type, action, parameters
        ORDER BY frequency DESC
    ''', (user_id,))
    
    operations = cursor.fetchall()
    
    # 分析各设备的常用操作
    device_patterns = defaultdict(list)
    for device_type, action, parameters, hour, frequency in operations:
        device_patterns[device_type].append({
            'action': action,
            'parameters': parameters,
            'frequency': frequency,
            'hour': hour
        })
    
    # 空调建议
    if 'air_conditioner' in device_patterns:
        ac_ops = device_patterns['air_conditioner']
        # 查找最常用的温度设置
        temp_settings = []
        for op in ac_ops:
            if op['parameters']:
                try:
                    params = json.loads(op['parameters'])
                    if 'temperature' in params:
                        temp_settings.append((params['temperature'], op['frequency']))
                except:
                    pass
        
        if temp_settings:
            # 按频率排序，取最常用的温度
            temp_settings.sort(key=lambda x: x[1], reverse=True)
            recommended_temp = temp_settings[0][0]
            total_samples = sum([t[1] for t in temp_settings])
            
            recommendations.append({
                'device_type': 'air_conditioner',
                'device_name': '空调',
                'action': 'set_temperature',
                'parameters': {'temperature': recommended_temp},
                'reason': f'根据您的历史习惯，睡觉时通常设置温度为{recommended_temp}°C',
                'confidence': min(0.95, total_samples / 10),  # 样本越多置信度越高
                'sample_count': total_samples
            })
        
        # 检查是否有开关空调的习惯
        power_ops = [op for op in ac_ops if 'power' in op['action'].lower() or '开' in op['action'] or '关' in op['action']]
        if power_ops:
            most_common_power = max(power_ops, key=lambda x: x['frequency'])
            recommendations.append({
                'device_type': 'air_conditioner',
                'device_name': '空调',
                'action': most_common_power['action'],
                'parameters': {},
                'reason': f'根据历史习惯，建议执行：{most_common_power["action"]}',
                'confidence': 0.8,
                'sample_count': most_common_power['frequency']
            })
    
    # 床头灯建议
    if 'bedside_lamp' in device_patterns:
        lamp_ops = device_patterns['bedside_lamp']
        
        # 查找亮度和色温设置
        brightness_settings = []
        color_temp_settings = []
        
        for op in lamp_ops:
            if op['parameters']:
                try:
                    params = json.loads(op['parameters'])
                    if 'brightness' in params:
                        brightness_settings.append((params['brightness'], op['frequency']))
                    if 'color_temp' in params or 'ct' in params:
                        temp_val = params.get('color_temp') or params.get('ct')
                        color_temp_settings.append((temp_val, op['frequency']))
                except:
                    pass
        
        if brightness_settings:
            brightness_settings.sort(key=lambda x: x[1], reverse=True)
            recommended_brightness = brightness_settings[0][0]
            
            recommendations.append({
                'device_type': 'bedside_lamp',
                'device_name': '床头灯',
                'action': 'set_brightness',
                'parameters': {'brightness': recommended_brightness},
                'reason': f'根据您的睡眠习惯，建议床头灯亮度设为{recommended_brightness}%',
                'confidence': 0.85,
                'sample_count': sum([b[1] for b in brightness_settings])
            })
        
        if color_temp_settings:
            color_temp_settings.sort(key=lambda x: x[1], reverse=True)
            recommended_ct = color_temp_settings[0][0]
            
            recommendations.append({
                'device_type': 'bedside_lamp',
                'device_name': '床头灯',
                'action': 'set_color_temp',
                'parameters': {'color_temp': recommended_ct},
                'reason': f'根据您的习惯，建议床头灯色温设为{recommended_ct}K',
                'confidence': 0.85,
                'sample_count': sum([c[1] for c in color_temp_settings])
            })
    
    # 空气净化器建议
    if 'air_cleaner' in device_patterns:
        cleaner_ops = device_patterns['air_cleaner']
        
        # 查找模式设置（睡眠模式）
        mode_ops = [op for op in cleaner_ops if 'mode' in op['action'].lower() or '模式' in op['action']]
        if mode_ops:
            most_common_mode = max(mode_ops, key=lambda x: x['frequency'])
            recommendations.append({
                'device_type': 'air_cleaner',
                'device_name': '空气净化器',
                'action': most_common_mode['action'],
                'parameters': json.loads(most_common_mode['parameters']) if most_common_mode['parameters'] else {},
                'reason': f'睡觉时建议使用：{most_common_mode["action"]}',
                'confidence': 0.8,
                'sample_count': most_common_mode['frequency']
            })
    
    # 如果没有历史数据，返回空列表（后续可以通过MCP搜索获取通用建议）
    return recommendations


def _analyze_wakeup_scene(cursor, user_id: str, current_hour: int, current_month: int) -> List[Dict]:
    """分析起床场景的历史习惯"""
    recommendations = []
    
    # 查询早晨时段（6:00-10:00）的历史操作
    cursor.execute('''
        SELECT device_type, action, parameters, COUNT(*) as frequency
        FROM device_operations
        WHERE user_id = ? 
        AND success = 1
        AND CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 6 AND 10
        GROUP BY device_type, action, parameters
        ORDER BY frequency DESC
    ''', (user_id,))
    
    operations = cursor.fetchall()
    
    for device_type, action, parameters, frequency in operations[:5]:  # 取前5个最常见操作
        params = json.loads(parameters) if parameters else {}
        recommendations.append({
            'device_type': device_type,
            'action': action,
            'parameters': params,
            'reason': f'根据您早晨的使用习惯',
            'confidence': min(0.9, frequency / 10),
            'sample_count': frequency
        })
    
    return recommendations


def _analyze_leaving_scene(cursor, user_id: str, current_hour: int) -> List[Dict]:
    """分析离家场景"""
    recommendations = []
    
    # 离家通常是关闭设备
    cursor.execute('''
        SELECT device_type, action, COUNT(*) as frequency
        FROM device_operations
        WHERE user_id = ? 
        AND success = 1
        AND (action LIKE '%关%' OR action LIKE '%off%' OR action LIKE '%关闭%')
        GROUP BY device_type, action
        ORDER BY frequency DESC
    ''', (user_id,))
    
    operations = cursor.fetchall()
    
    for device_type, action, frequency in operations:
        recommendations.append({
            'device_type': device_type,
            'action': action,
            'parameters': {},
            'reason': '离家时建议关闭设备以节能',
            'confidence': 0.95,
            'sample_count': frequency
        })
    
    return recommendations


def _analyze_arriving_scene(cursor, user_id: str, current_hour: int, current_month: int) -> List[Dict]:
    """分析回家场景"""
    recommendations = []
    
    # 查询下午到晚上时段（17:00-21:00）的操作
    cursor.execute('''
        SELECT device_type, action, parameters, COUNT(*) as frequency
        FROM device_operations
        WHERE user_id = ? 
        AND success = 1
        AND CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 17 AND 21
        GROUP BY device_type, action, parameters
        ORDER BY frequency DESC
        LIMIT 5
    ''', (user_id,))
    
    operations = cursor.fetchall()
    
    for device_type, action, parameters, frequency in operations:
        params = json.loads(parameters) if parameters else {}
        recommendations.append({
            'device_type': device_type,
            'action': action,
            'parameters': params,
            'reason': f'根据您回家后的使用习惯',
            'confidence': min(0.9, frequency / 8),
            'sample_count': frequency
        })
    
    return recommendations


def _analyze_work_scene(cursor, user_id: str, current_hour: int, current_month: int) -> List[Dict]:
    """分析工作/学习场景"""
    recommendations = []
    
    # 工作时段（9:00-18:00）
    cursor.execute('''
        SELECT device_type, action, parameters, COUNT(*) as frequency
        FROM device_operations
        WHERE user_id = ? 
        AND success = 1
        AND CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 9 AND 18
        GROUP BY device_type, action, parameters
        ORDER BY frequency DESC
        LIMIT 5
    ''', (user_id,))
    
    operations = cursor.fetchall()
    
    for device_type, action, parameters, frequency in operations:
        params = json.loads(parameters) if parameters else {}
        recommendations.append({
            'device_type': device_type,
            'action': action,
            'parameters': params,
            'reason': f'根据您工作时的使用偏好',
            'confidence': min(0.85, frequency / 10),
            'sample_count': frequency
        })
    
    return recommendations


def _analyze_general_scene(cursor, user_id: str, scene_type: str, current_hour: int) -> List[Dict]:
    """通用场景分析"""
    recommendations = []
    
    # 查询最近类似操作
    cursor.execute('''
        SELECT device_type, action, parameters, COUNT(*) as frequency
        FROM device_operations
        WHERE user_id = ? 
        AND success = 1
        GROUP BY device_type, action, parameters
        ORDER BY frequency DESC
        LIMIT 3
    ''', (user_id,))
    
    operations = cursor.fetchall()
    
    for device_type, action, parameters, frequency in operations:
        params = json.loads(parameters) if parameters else {}
        recommendations.append({
            'device_type': device_type,
            'action': action,
            'parameters': params,
            'reason': f'根据您的常用操作',
            'confidence': 0.6,
            'sample_count': frequency
        })
    
    return recommendations


@tool("analyze_user_patterns", description="分析用户的设备使用模式和习惯，识别时间规律、设备偏好等")
def analyze_user_patterns(user_id: str = "default_user", days: int = 30) -> str:
    """
    分析用户的设备使用模式
    
    Args:
        user_id: 用户ID
        days: 分析的天数范围
        
    Returns:
        JSON格式的分析结果
    """
    try:
        conn = db_config.get_raw_connection()
        cursor = conn.cursor()
        
        _ensure_tables_exist(cursor)
        
        # 计算起始日期
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # 分析设备使用频率
        cursor.execute('''
            SELECT device_type, COUNT(*) as usage_count
            FROM device_operations
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY device_type
            ORDER BY usage_count DESC
        ''', (user_id, start_date))
        
        device_usage = [{'device_type': row[0], 'usage_count': row[1]} for row in cursor.fetchall()]
        
        # 分析时间模式
        cursor.execute('''
            SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, COUNT(*) as count
            FROM device_operations
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY hour
            ORDER BY count DESC
        ''', (user_id, start_date))
        
        time_patterns = [{'hour': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # 分析最常用的操作
        cursor.execute('''
            SELECT device_type, action, COUNT(*) as frequency
            FROM device_operations
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY device_type, action
            ORDER BY frequency DESC
            LIMIT 10
        ''', (user_id, start_date))
        
        common_actions = [
            {'device_type': row[0], 'action': row[1], 'frequency': row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        result = {
            'user_id': user_id,
            'analysis_period': f'{days} days',
            'device_usage': device_usage,
            'time_patterns': time_patterns,
            'common_actions': common_actions,
            'peak_usage_hour': time_patterns[0]['hour'] if time_patterns else None,
            'most_used_device': device_usage[0]['device_type'] if device_usage else None,
            'generated_at': datetime.now().isoformat()
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"分析用户模式失败: {e}", exc_info=True)
        return json.dumps({
            'error': str(e),
            'message': '分析用户模式失败'
        }, indent=2, ensure_ascii=False)


@tool("get_device_preferences", description="获取用户对特定设备的偏好设置，如空调的常用温度、灯光的常用亮度等")
def get_device_preferences(device_type: str, user_id: str = "default_user") -> str:
    """
    获取用户对特定设备的偏好设置
    
    Args:
        device_type: 设备类型
        user_id: 用户ID
        
    Returns:
        JSON格式的偏好设置
    """
    try:
        conn = db_config.get_raw_connection()
        cursor = conn.cursor()
        
        _ensure_tables_exist(cursor)
        
        # 查询该设备的所有操作
        cursor.execute('''
            SELECT action, parameters, COUNT(*) as frequency
            FROM device_operations
            WHERE user_id = ? AND device_type = ? AND success = 1
            GROUP BY action, parameters
            ORDER BY frequency DESC
        ''', (user_id, device_type))
        
        operations = cursor.fetchall()
        conn.close()
        
        if not operations:
            return json.dumps({
                'device_type': device_type,
                'user_id': user_id,
                'message': f'暂无{device_type}的使用记录',
                'preferences': {}
            }, indent=2, ensure_ascii=False)
        
        # 分析参数偏好
        preferences = {}
        parameter_stats = defaultdict(list)
        
        for action, parameters, frequency in operations:
            if parameters:
                try:
                    params = json.loads(parameters)
                    for key, value in params.items():
                        parameter_stats[key].append((value, frequency))
                except:
                    pass
        
        # 计算每个参数的最常用值
        for param_name, values in parameter_stats.items():
            values.sort(key=lambda x: x[1], reverse=True)
            most_common = values[0]
            preferences[param_name] = {
                'preferred_value': most_common[0],
                'frequency': most_common[1],
                'alternatives': [v[0] for v in values[1:4]]  # 其他常用值
            }
        
        # 最常用的操作
        most_common_action = operations[0]
        
        result = {
            'device_type': device_type,
            'user_id': user_id,
            'most_common_action': {
                'action': most_common_action[0],
                'frequency': most_common_action[2]
            },
            'parameter_preferences': preferences,
            'total_operations': sum([op[2] for op in operations]),
            'generated_at': datetime.now().isoformat()
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"获取设备偏好失败: {e}", exc_info=True)
        return json.dumps({
            'error': str(e),
            'message': '获取设备偏好失败'
        }, indent=2, ensure_ascii=False)


@tool("predict_next_action", description="根据当前时间和上下文，预测用户接下来可能需要的设备操作")
def predict_next_action(user_id: str = "default_user", current_context: Dict[str, Any] = None) -> str:
    """
    预测用户接下来可能的操作
    
    Args:
        user_id: 用户ID
        current_context: 当前上下文（时间、环境等）
        
    Returns:
        JSON格式的预测结果
    """
    try:
        if current_context is None:
            current_context = {}
            
        conn = db_config.get_raw_connection()
        cursor = conn.cursor()
        
        _ensure_tables_exist(cursor)
        
        current_hour = datetime.now().hour
        
        # 查询当前时间段（前后1小时）的历史操作
        cursor.execute('''
            SELECT device_type, action, parameters, COUNT(*) as frequency
            FROM device_operations
            WHERE user_id = ?
            AND CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN ? AND ?
            AND success = 1
            GROUP BY device_type, action, parameters
            ORDER BY frequency DESC
            LIMIT 5
        ''', (user_id, max(0, current_hour - 1), min(23, current_hour + 1)))
        
        predictions = []
        for device_type, action, parameters, frequency in cursor.fetchall():
            params = json.loads(parameters) if parameters else {}
            predictions.append({
                'device_type': device_type,
                'action': action,
                'parameters': params,
                'probability': min(0.95, frequency / 10),
                'reason': f'您在{current_hour}:00左右经常执行此操作',
                'sample_count': frequency
            })
        
        conn.close()
        
        result = {
            'user_id': user_id,
            'current_time': datetime.now().isoformat(),
            'current_hour': current_hour,
            'predictions': predictions,
            'message': '基于历史习惯的操作预测' if predictions else '暂无足够的历史数据进行预测'
        }
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"预测用户操作失败: {e}", exc_info=True)
        return json.dumps({
            'error': str(e),
            'message': '预测用户操作失败'
        }, indent=2, ensure_ascii=False)

