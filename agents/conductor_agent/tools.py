from langchain_core.tools import tool
import json
import httpx
from pydantic import BaseModel, Field
from typing import Dict, List, Any
import asyncio
import sqlite3
from datetime import datetime


# 数据库文件路径
DB_PATH = "user_behavior.db"

# 注册的代理服务配置
REGISTERED_AGENTS = {
    "air_conditioner": {
        "name": "空调代理",
        "url": "http://localhost:12000",
        "description": "控制家庭空调系统",
        "capabilities": ["温度控制", "电源管理", "模式切换"]
    },
    "air_cleaner": {
        "name": "空气净化器代理", 
        "url": "http://localhost:12001",
        "description": "控制空气净化器设备",
        "capabilities": ["空气质量监测", "净化模式控制", "滤网状态"]
    },
    "data_mining": {
        "name": "数据挖掘代理",
        "url": "http://localhost:12003",
        "description": "分析用户行为数据",
        "capabilities": ["习惯分析", "偏好预测", "历史查询", "统计分析"]
    }
}


@tool("list_available_agents", description="列出所有可用的代理服务")
def list_available_agents():
    """获取所有已注册的代理服务列表"""
    try:
        agents_info = []
        for agent_id, config in REGISTERED_AGENTS.items():
            agents_info.append({
                "id": agent_id,
                "name": config["name"],
                "url": config["url"],
                "description": config["description"],
                "capabilities": config["capabilities"]
            })
        
        return json.dumps({
            "message": "成功获取代理列表",
            "agents": agents_info,
            "total_count": len(agents_info)
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "获取代理列表失败"
        }, indent=2, ensure_ascii=False)


class AgentCommandArgs(BaseModel):
    agent_id: str = Field(..., description="目标代理的ID")
    command: str = Field(..., description="要执行的命令或请求")


@tool("execute_agent_command", args_schema=AgentCommandArgs, description="向指定代理发送命令")
def execute_agent_command(agent_id: str, command: str):
    """向指定的代理发送命令并获取响应"""
    try:
        if agent_id not in REGISTERED_AGENTS:
            return json.dumps({
                "error": f"代理 {agent_id} 未找到",
                "available_agents": list(REGISTERED_AGENTS.keys())
            }, indent=2, ensure_ascii=False)
        
        agent_config = REGISTERED_AGENTS[agent_id]
        agent_url = agent_config["url"]
        
        # 这里应该实现实际的HTTP请求到代理服务
        # 由于这是模拟，我们返回一个模拟响应
        return json.dumps({
            "message": f"命令已发送到 {agent_config['name']}",
            "agent_id": agent_id,
            "command": command,
            "status": "success",
            "response": f"代理 {agent_config['name']} 已处理命令: {command}"
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "执行代理命令失败"
        }, indent=2, ensure_ascii=False)


@tool("get_agent_status", description="获取所有代理的运行状态")
def get_agent_status():
    """检查所有注册代理的运行状态"""
    try:
        status_info = []
        for agent_id, config in REGISTERED_AGENTS.items():
            # 这里应该实现实际的健康检查
            # 模拟所有代理都在线
            status_info.append({
                "agent_id": agent_id,
                "name": config["name"],
                "status": "online",
                "url": config["url"],
                "last_check": "2024-01-01T00:00:00Z"
            })
        
        return json.dumps({
            "message": "代理状态检查完成",
            "agents_status": status_info,
            "summary": {
                "total": len(status_info),
                "online": len([s for s in status_info if s["status"] == "online"]),
                "offline": len([s for s in status_info if s["status"] == "offline"])
            }
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "获取代理状态失败"
        }, indent=2, ensure_ascii=False)


class DeviceControlArgs(BaseModel):
    device_type: str = Field(..., description="设备类型 (air_conditioner, air_cleaner)")
    action: str = Field(..., description="要执行的操作")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="操作参数")


@tool("control_device", args_schema=DeviceControlArgs, description="控制智能设备")
def control_device(device_type: str, action: str, parameters: Dict[str, Any] = None):
    """统一的设备控制接口"""
    try:
        if parameters is None:
            parameters = {}
            
        if device_type not in REGISTERED_AGENTS:
            return json.dumps({
                "error": f"设备类型 {device_type} 不支持",
                "supported_types": list(REGISTERED_AGENTS.keys())
            }, indent=2, ensure_ascii=False)
        
        agent_config = REGISTERED_AGENTS[device_type]
        
        # 构建命令
        command = f"{action}"
        if parameters:
            param_str = ", ".join([f"{k}={v}" for k, v in parameters.items()])
            command += f" ({param_str})"
        
        # 记录操作日志到数据库
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # 确保表存在
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
            
            # 插入操作记录
            cursor.execute('''
                INSERT INTO device_operations 
                (user_id, device_type, device_name, action, parameters, success, response)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                "default_user",  # 默认用户ID，实际应用中应该从上下文获取
                device_type,
                agent_config["name"],
                action,
                json.dumps(parameters) if parameters else None,
                True,
                "Command sent successfully"
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as log_error:
            print(f"日志记录失败: {log_error}")
        
        return json.dumps({
            "message": f"设备控制命令已发送",
            "device_type": device_type,
            "device_name": agent_config["name"],
            "action": action,
            "parameters": parameters,
            "command": command,
            "status": "success",
            "logged": True
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "设备控制失败"
        }, indent=2, ensure_ascii=False)


@tool("get_system_overview", description="获取整个智能家居系统的概览")
def get_system_overview():
    """获取智能家居系统的整体状态概览"""
    try:
        overview = {
            "system_name": "智能家居管理系统",
            "total_agents": len(REGISTERED_AGENTS),
            "agents": [],
            "system_status": "running",
            "last_updated": "2024-01-01T00:00:00Z"
        }
        
        for agent_id, config in REGISTERED_AGENTS.items():
            overview["agents"].append({
                "id": agent_id,
                "name": config["name"],
                "status": "online",
                "capabilities": config["capabilities"]
            })
        
        return json.dumps(overview, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "获取系统概览失败"
        }, indent=2, ensure_ascii=False)


@tool("analyze_user_behavior", description="分析用户行为数据")
def analyze_user_behavior(user_id: str = "default_user", days: int = 30):
    """分析用户行为数据，调用数据挖掘代理"""
    try:
        # 这里应该调用数据挖掘代理的API
        # 由于是模拟，我们直接返回一个分析结果
        return json.dumps({
            "message": f"用户 {user_id} 行为分析完成",
            "user_id": user_id,
            "analysis_period": f"{days} days",
            "insights": [
                {
                    "type": "device_usage",
                    "data": {"air_conditioner": 15, "air_cleaner": 8},
                    "description": "设备使用频率"
                },
                {
                    "type": "time_pattern",
                    "data": {"peak_hours": [19, 20, 21], "usage_count": 12},
                    "description": "使用时间模式"
                },
                {
                    "type": "temperature_preference",
                    "data": {"average": 25.5, "range": [22, 28]},
                    "description": "温度偏好"
                }
            ],
            "recommendations": [
                "建议在晚上7-9点自动调节空调温度",
                "根据历史数据，推荐设置温度为25.5度",
                "可以考虑在空气质量较差时自动开启空气净化器"
            ],
            "generated_at": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "用户行为分析失败"
        }, indent=2, ensure_ascii=False)


@tool("get_user_insights", description="获取用户洞察和建议")
def get_user_insights(user_id: str = "default_user"):
    """获取基于历史数据的用户洞察和个性化建议"""
    try:
        # 查询数据库获取用户操作历史
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取最近的操作记录
        cursor.execute('''
            SELECT device_type, action, parameters, timestamp
            FROM device_operations 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 20
        ''', (user_id,))
        
        operations = cursor.fetchall()
        conn.close()
        
        if not operations:
            return json.dumps({
                "message": f"用户 {user_id} 暂无操作记录",
                "user_id": user_id,
                "insights": [],
                "suggestions": ["开始使用智能设备以获得个性化建议"]
            }, indent=2, ensure_ascii=False)
        
        # 分析操作模式
        device_usage = {}
        time_patterns = []
        temperature_settings = []
        
        for op in operations:
            device_type, action, parameters, timestamp = op
            
            # 统计设备使用
            if device_type not in device_usage:
                device_usage[device_type] = 0
            device_usage[device_type] += 1
            
            # 分析时间模式
            hour = datetime.fromisoformat(timestamp).hour
            time_patterns.append(hour)
            
            # 分析温度设置
            if device_type == 'air_conditioner' and action == 'set_temperature' and parameters:
                try:
                    params = json.loads(parameters)
                    if 'temperature' in params:
                        temperature_settings.append(params['temperature'])
                except:
                    pass
        
        # 生成洞察
        insights = []
        
        if device_usage:
            most_used_device = max(device_usage, key=device_usage.get)
            insights.append({
                "type": "most_used_device",
                "data": {"device": most_used_device, "count": device_usage[most_used_device]},
                "description": f"最常使用的设备是 {most_used_device}"
            })
        
        if time_patterns:
            from collections import Counter
            time_counter = Counter(time_patterns)
            peak_hour = time_counter.most_common(1)[0][0]
            insights.append({
                "type": "peak_usage_time",
                "data": {"hour": peak_hour, "count": time_counter[peak_hour]},
                "description": f"最常使用设备的时间是 {peak_hour}:00"
            })
        
        if temperature_settings:
            avg_temp = sum(temperature_settings) / len(temperature_settings)
            insights.append({
                "type": "temperature_preference",
                "data": {"average": round(avg_temp, 1), "count": len(temperature_settings)},
                "description": f"平均偏好温度是 {round(avg_temp, 1)} 度"
            })
        
        # 生成建议
        suggestions = []
        if most_used_device == 'air_conditioner':
            suggestions.append("建议设置空调自动模式，根据时间自动调节")
        if peak_hour in [19, 20, 21]:
            suggestions.append("检测到您通常在晚上使用设备，建议设置定时任务")
        if temperature_settings and avg_temp > 26:
            suggestions.append("建议适当降低温度设置以节省能源")
        
        return json.dumps({
            "message": f"用户 {user_id} 洞察分析完成",
            "user_id": user_id,
            "total_operations": len(operations),
            "insights": insights,
            "suggestions": suggestions,
            "generated_at": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "获取用户洞察失败"
        }, indent=2, ensure_ascii=False)