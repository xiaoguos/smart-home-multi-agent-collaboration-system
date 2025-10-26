from langchain_core.tools import tool
import json
from pydantic import BaseModel, Field
from typing import Dict, Any
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from datetime import datetime
import httpx
from a2a.client import ClientFactory, A2ACardResolver
from a2a.types import Message, Part
from a2a.client.client import ClientConfig

# 设置日志
logger = logging.getLogger(__name__)

# 线程池用于执行异步操作
_executor = ThreadPoolExecutor(max_workers=5)

# 注册的代理服务配置
# 端口分配：
# - conductor_agent: 12000
# - air_conditioner_agent: 12001
# - air_cleaner_agent: 12002
# - data_mining_agent: 12003
# - bedside_lamp_agent: 12004
REGISTERED_AGENTS = {
    "air_conditioner": {
        "name": "空调代理",
        "url": "http://localhost:12001",
        "description": "控制家庭空调系统",
        "capabilities": ["温度控制", "电源管理", "模式切换"]
    },
    "air_cleaner": {
        "name": "空气净化器代理", 
        "url": "http://localhost:12002",
        "description": "控制空气净化器设备",
        "capabilities": ["空气质量监测", "净化模式控制", "滤网状态", "风扇等级控制", "PM2.5监测", "湿度监测"]
    },
    "data_mining": {
        "name": "数据挖掘代理",
        "url": "http://localhost:12003",
        "description": "分析用户行为数据",
        "capabilities": ["习惯分析", "偏好预测", "历史查询", "统计分析"]
    },
    "bedside_lamp": {
        "name": "床头灯代理",
        "url": "http://localhost:12004",
        "description": "控制Yeelink床头灯设备",
        "capabilities": ["电源控制", "亮度调节", "色温设置", "颜色设置", "场景模式", "阅读模式", "睡眠模式", "浪漫模式", "夜灯模式"]
    }
}


def _run_async_in_thread(coro):
    """
    在独立线程中运行异步代码，避免事件循环冲突
    """
    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    
    future = _executor.submit(run_in_new_loop)
    return future.result(timeout=120)  # 增加总体超时到120秒


async def _call_a2a_agent_async(agent_url: str, command: str, timeout: float = 90.0) -> Dict[str, Any]:
    """
    通过 A2A 协议调用其他 agent (异步版本)
    
    Args:
        agent_url: agent 的基础 URL
        command: 要发送给 agent 的命令
        timeout: 请求超时时间（秒）
        
    Returns:
        包含 agent 响应的字典
    """
    logger.info(f"开始调用 A2A agent: {agent_url}, 命令: {command}")
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as httpx_client:
            logger.info(f"正在获取 agent 卡片: {agent_url}")
            # 获取 agent 卡片
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=agent_url)
            agent_card = await resolver.get_agent_card()
            logger.info(f"成功获取 agent 卡片: {agent_card.name}")
            
            # 创建客户端配置
            config = ClientConfig(
                streaming=False,
                polling=False,
                httpx_client=httpx_client,
                supported_transports=["JSONRPC", "http_json"],
                use_client_preference=False,
                accepted_output_modes=["text", "text/plain"]
            )
            
            # 创建客户端
            factory = ClientFactory(config=config)
            client = factory.create(card=agent_card)
            logger.info("客户端创建成功，准备发送消息")
            
            # 创建消息
            message = Message(
                context_id=str(uuid4()),
                role='user',
                parts=[Part(kind='text', text=command)],
                message_id=uuid4().hex
            )
            
            # 发送消息并收集响应
            logger.info("开始发送消息并等待响应...")
            responses = []
            final_content = ""
            
            async for response in client.send_message(message):
                logger.info(f"收到响应: {type(response)}")
                
                # 提取实际的文本内容
                if hasattr(response, 'artifacts') and response.artifacts:
                    # 从artifacts中提取文本内容
                    for artifact in response.artifacts:
                        if hasattr(artifact, 'parts'):
                            for part in artifact.parts:
                                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                    final_content = part.root.text
                                elif hasattr(part, 'text'):
                                    final_content = part.text
                
                # 如果没有artifacts，尝试从message中提取
                if not final_content and hasattr(response, 'message'):
                    msg = response.message
                    if hasattr(msg, 'parts') and msg.parts:
                        for part in msg.parts:
                            if hasattr(part, 'text'):
                                final_content = part.text
                            elif hasattr(part, 'root') and hasattr(part.root, 'text'):
                                final_content = part.root.text
                
                # 保留原始响应用于调试
                if hasattr(response, 'model_dump'):
                    responses.append(response.model_dump(mode='json', exclude_none=True))
                else:
                    responses.append(str(response))
            
            logger.info(f"成功收集 {len(responses)} 个响应，提取的文本内容长度: {len(final_content)}")
            return {
                "success": True,
                "content": final_content,  # 只返回文本内容
                "responses": responses,  # 保留完整响应用于调试
                "agent_url": agent_url,
                "command": command
            }
            
    except Exception as e:
        logger.error(f"调用 A2A agent 失败: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "agent_url": agent_url,
            "command": command
        }


def call_a2a_agent(agent_url: str, command: str, timeout: float = 90.0) -> Dict[str, Any]:
    """
    通过 A2A 协议调用其他 agent (同步包装)
    
    Args:
        agent_url: agent 的基础 URL
        command: 要发送给 agent 的命令
        timeout: 请求超时时间（秒）
        
    Returns:
        包含 agent 响应的字典
    """
    coro = _call_a2a_agent_async(agent_url, command, timeout)
    return _run_async_in_thread(coro)


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
        
        logger.info(f"执行代理命令: agent_id={agent_id}, command={command}")
        
        # 调用 A2A agent (现在是同步函数，会在线程中运行)
        result = call_a2a_agent(agent_url, command)
        
        if result.get("success"):
            logger.info(f"成功调用 {agent_config['name']}")
            # 直接返回agent的内容，而不是包装在JSON中
            content = result.get("content", "")
            if content:
                return content
            else:
                # 如果没有提取到content，返回一个简单的成功消息
                return f"成功调用 {agent_config['name']}，命令: {command}"
        else:
            logger.error(f"调用 {agent_config['name']} 失败: {result.get('error')}")
            return json.dumps({
                "message": f"调用 {agent_config['name']} 失败",
                "agent_id": agent_id,
                "agent_name": agent_config["name"],
                "command": command,
                "status": "failed",
                "error": result.get("error")
            }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"执行代理命令异常: {str(e)}", exc_info=True)
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
    device_type: str = Field(..., description="设备类型 (air_conditioner, air_cleaner, bedside_lamp)")
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
        agent_url = agent_config["url"]
        
        # 构建命令
        command = f"{action}"
        if parameters:
            param_str = ", ".join([f"{k}={v}" for k, v in parameters.items()])
            command += f" ({param_str})"
        
        logger.info(f"控制设备: device_type={device_type}, command={command}")
        
        # 调用 A2A agent 执行实际控制 (现在是同步函数，会在线程中运行)
        result = call_a2a_agent(agent_url, command)
        
        success = result.get("success", False)
        if success:
            logger.info(f"成功控制 {agent_config['name']}")
            # 直接返回agent的内容
            content = result.get("content", "")
            if content:
                return content
            else:
                # 如果没有提取到content，返回一个简单的成功消息
                return f"成功控制 {agent_config['name']}：{action}"
        else:
            logger.error(f"控制 {agent_config['name']} 失败: {result.get('error')}")
            return json.dumps({
                "message": f"控制 {agent_config['name']} 失败",
                "device_type": device_type,
                "device_name": agent_config["name"],
                "action": action,
                "parameters": parameters,
                "command": command,
                "status": "failed",
                "error": result.get("error")
            }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"设备控制异常: {str(e)}", exc_info=True)
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
        # 简化版本：返回模拟的用户洞察
        # 实际应用中应该调用数据挖掘代理获取真实数据
        return json.dumps({
            "message": f"用户 {user_id} 洞察分析完成",
            "user_id": user_id,
            "insights": [
                {
                    "type": "device_usage_pattern",
                    "description": "建议通过数据挖掘代理获取详细的使用习惯分析"
                },
                {
                    "type": "recommendation",
                    "description": "使用 query_data_mining_agent 工具获取个性化建议"
                }
            ],
            "suggestions": [
                "建议使用数据挖掘代理进行深度分析",
                "可以通过描述场景（如'我要睡觉了'）获取智能建议"
            ],
            "generated_at": datetime.now().isoformat()
        }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "获取用户洞察失败"
        }, indent=2, ensure_ascii=False)


class DataMiningQueryArgs(BaseModel):
    query: str = Field(..., description="给数据挖掘代理的查询内容，如'我要睡觉了'、'分析我对空调的偏好'等")
    user_id: str = Field(default="default_user", description="用户ID")


@tool("query_data_mining_agent", args_schema=DataMiningQueryArgs, 
     description="调用数据挖掘代理分析用户场景和习惯。当用户描述场景（如'我睡觉了'）或需要个性化建议时使用此工具")
def query_data_mining_agent(query: str, user_id: str = "default_user"):
    """
    调用数据挖掘代理，进行场景识别和习惯分析
    
    适用场景：
    - 用户描述了一个场景（如"我要睡觉了"、"起床了"、"要出门了"）
    - 需要获取特定场景下的设备控制建议
    - 需要分析用户对某个设备的使用偏好
    
    Args:
        query: 用户的查询或场景描述
        user_id: 用户ID
        
    Returns:
        数据挖掘agent的分析结果，包含场景识别和设备控制建议
    """
    try:
        agent_config = REGISTERED_AGENTS.get("data_mining")
        if not agent_config:
            return json.dumps({
                "error": "数据挖掘代理未配置",
                "message": "请检查数据挖掘代理是否已启动"
            }, indent=2, ensure_ascii=False)
        
        agent_url = agent_config["url"]
        
        # 构建完整的查询
        full_query = f"{query} (用户ID: {user_id})"
        
        logger.info(f"调用数据挖掘代理: query={full_query}")
        
        # 调用数据挖掘代理
        result = call_a2a_agent(agent_url, full_query, timeout=90.0)
        
        if result.get("success"):
            logger.info("数据挖掘代理调用成功")
            # 直接返回数据挖掘agent的内容
            content = result.get("content", "")
            if content:
                return content
            else:
                return f"数据挖掘分析完成，查询: {query}"
        else:
            logger.error(f"数据挖掘代理调用失败: {result.get('error')}")
            return json.dumps({
                "message": "数据挖掘分析失败",
                "query": query,
                "user_id": user_id,
                "status": "failed",
                "error": result.get("error"),
                "suggestion": "可能是数据挖掘代理未启动或网络问题"
            }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"调用数据挖掘代理异常: {str(e)}", exc_info=True)
        return json.dumps({
            "error": str(e),
            "message": "调用数据挖掘代理失败"
        }, indent=2, ensure_ascii=False)


# ==================== 小米设备信息直接获取 ====================

def _get_xiaomi_devices_direct(username: str, password: str, server: str = "cn", skip_login: bool = False) -> str:
    """直接获取小米设备信息，不使用 MCP"""
    import sys
    import os
    
    try:
        # 导入小米设备连接器
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        mcp_dir = os.path.join(current_dir, "mcp")
        if mcp_dir not in sys.path:
            sys.path.insert(0, mcp_dir)
        
        from divice import XiaomiCloudConnector
        
        logger.info(f"开始获取小米设备信息: {username}, 服务器: {server}, 跳过登录: {skip_login}")
        
        # 1. 创建连接器
        connector = XiaomiCloudConnector(username, password)
        
        # 如果不跳过登录，则执行真正的登录
        if not skip_login:
            logged_in = connector.login()
            if not logged_in:
                return json.dumps({
                    "success": False,
                    "message": "小米账号登录失败，请检查用户名和密码",
                }, ensure_ascii=False, indent=2)
            logger.info("登录成功，开始获取设备列表")
        else:
            # 跳过登录，直接使用 divice.py 中的默认 token 和参数
            logger.info("跳过登录，使用默认参数")
        
        # 2. 获取所有家庭
        all_homes = []
        
        # 获取用户自己的家庭
        homes = connector.get_homes(server)
        if homes is not None and 'result' in homes and 'homelist' in homes['result']:
            for h in homes['result']['homelist']:
                all_homes.append({
                    'home_id': h['id'],
                    'home_owner': connector.userId,
                    'home_name': h.get('name', '未命名家庭')
                })
        
        # 获取共享家庭
        dev_cnt = connector.get_dev_cnt(server)
        if dev_cnt is not None and 'result' in dev_cnt and 'share' in dev_cnt['result']:
            share_families = dev_cnt['result']['share'].get('share_family', [])
            for h in share_families:
                all_homes.append({
                    'home_id': h['home_id'],
                    'home_owner': h['home_owner'],
                    'home_name': h.get('name', '共享家庭')
                })
        
        if len(all_homes) == 0:
            return json.dumps({
                "success": False,
                "message": f"在服务器 {server} 上未找到任何家庭",
            }, ensure_ascii=False, indent=2)
        
        # 3. 获取所有设备
        all_devices = []
        for home in all_homes:
            devices = connector.get_devices(server, home['home_id'], home['home_owner'])
            
            if devices is not None and 'result' in devices and 'device_info' in devices['result']:
                device_list = devices['result']['device_info']
                
                if device_list:
                    for device in device_list:
                        device_data = {
                            "home_name": home.get('home_name'),
                            "home_id": home['home_id'],
                            "name": device.get('name', '未命名设备'),
                            "did": device.get('did'),
                            "mac": device.get('mac'),
                            "ip": device.get('localip'),
                            "token": device.get('token'),
                            "model": device.get('model'),
                            "isOnline": device.get('isOnline', False),
                            "rssi": device.get('rssi'),
                        }
                        
                        # 如果是蓝牙设备，获取 BLE key
                        if device.get('did') and 'blt' in device['did']:
                            beaconkey = connector.get_beaconkey(server, device['did'])
                            if beaconkey and 'result' in beaconkey and 'beaconkey' in beaconkey['result']:
                                device_data['ble_key'] = beaconkey['result']['beaconkey']
                        
                        all_devices.append(device_data)
        
        logger.info(f"成功获取 {len(all_devices)} 个设备")
        
        return json.dumps({
            "success": True,
            "message": f"成功获取设备列表",
            "userId": connector.userId,
            "server": server,
            "total_homes": len(all_homes),
            "total_devices": len(all_devices),
            "devices": all_devices,
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取设备信息异常: {str(e)}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": f"获取设备信息异常: {str(e)}",
        }, ensure_ascii=False, indent=2)


class XiaomiDevicesArgs(BaseModel):
    username: str = Field(..., description="小米账号（邮箱、手机号或用户ID）")
    password: str = Field(..., description="小米账号密码")
    server: str = Field(default="cn", description="服务器区域，可选：cn, de, us, ru, tw, sg, in, i2")
    skip_login: bool = Field(default=False, description="是否跳过登录直接使用默认token")


@tool("get_xiaomi_devices", args_schema=XiaomiDevicesArgs,
     description="获取小米智能设备信，一次性完成登录和设备查询")
def get_xiaomi_devices(username: str, password: str, server: str = "cn", skip_login: bool = False):
    """
    获取小米智能设备信息（包含登录、获取设备列表等完整流程）
    
    Args:
        username: 小米账号（邮箱、手机号或用户ID）
        password: 小米账号密码
        server: 服务器区域（默认：cn）
        skip_login: 是否跳过登录，直接使用默认token（默认：False）
    
    Returns:
        设备列表，包含设备名称、ID、MAC地址、IP地址、Token、型号等
    """
    try:
        logger.info(f"正在获取小米设备信息: {username}, 服务器: {server}, 跳过登录: {skip_login}")
        # 直接调用获取函数，不使用 MCP
        return _get_xiaomi_devices_direct(username, password, server, skip_login)
    except Exception as e:
        logger.error(f"获取小米设备信息失败: {str(e)}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": f"获取设备信息失败: {str(e)}"
        }, ensure_ascii=False, indent=2)