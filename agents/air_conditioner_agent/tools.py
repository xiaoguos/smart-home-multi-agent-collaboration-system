from langchain_core.tools import tool
from miio import AirConditioningCompanionMcn02
import json
from pydantic import BaseModel, Field
import logging
import asyncio
import os

# 配置日志
logger = logging.getLogger(__name__)

# 默认配置 - 如果 MCP 不可用，会回退到这些配置
DEFAULT_SYSTEM_USER_ID = 1000000001  # admin 用户ID
DEFAULT_AC_NAME = "空调"
AC_IP = "192.168.110.123"  # 默认IP（回退用）
AC_TOKEN = "1724bf8d57b355173dfa08ae23367f86"  # 默认Token（回退用）
AC_MODEL = "lumi.acpartner.mcn02"

# 设备缓存（避免频繁查询）
_device_cache = {}


async def get_device_info_from_mcp(system_user_id: int, device_name: str = "空调") -> dict:
    """
    通过 MCP 服务获取设备信息
    
    注意：这需要 MCP 服务运行，如果不可用会返回 None
    """
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        
        # 获取当前文件所在目录，计算 MCP 服务路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        mcp_path = os.path.join(project_root, "mcp", "device_query_mcp.py")
        
        logger.info(f"正在通过 MCP 查询设备: {device_name}")
        
        # 创建 MCP 客户端
        server_params = StdioServerParameters(
            command="python",
            args=[mcp_path],
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 初始化
                await session.initialize()
                
                # 调用工具获取设备信息
                result = await session.call_tool(
                    "get_device_by_name",
                    arguments={
                        "system_user_id": system_user_id,
                        "device_name": device_name
                    }
                )
                
                # 解析结果
                result_data = json.loads(result.content[0].text if hasattr(result, 'content') else result)
                
                if result_data.get("success") and result_data.get("devices"):
                    devices = result_data["devices"]
                    if devices:
                        # 返回第一个匹配的设备
                        device = devices[0]
                        return device
                
                return None
                
    except Exception as e:
        logger.error(f"❌ 通过 MCP 获取设备信息失败: {e}")
        return None


def get_device_config(device_name: str = DEFAULT_AC_NAME, system_user_id: int = DEFAULT_SYSTEM_USER_ID) -> dict:
    """
    获取设备配置（优先使用 MCP，失败则使用缓存或默认配置）
    
    返回格式：
    {
        "ip": "192.168.110.123",
        "token": "1724bf8d57b355173dfa08ae23367f86",
        "model": "lumi.acpartner.mcn02",
        "name": "客厅空调"
    }
    """
    cache_key = f"{system_user_id}_{device_name}"
    
    # 检查缓存
    if cache_key in _device_cache:
        logger.info(f"使用缓存的设备信息: {device_name}")
        return _device_cache[cache_key]
    
    # 尝试通过 MCP 获取
    try:
        loop = asyncio.get_event_loop()
        device_info = loop.run_until_complete(
            get_device_info_from_mcp(system_user_id, device_name)
        )
        
        if device_info:
            config = {
                "ip": device_info.get("localip", ""),
                "token": device_info.get("token", ""),
                "model": device_info.get("model", ""),
                "name": device_info.get("name", device_name),
                "did": device_info.get("did", ""),
                "isOnline": device_info.get("isOnline", False),
            }
            
            # 缓存设备信息（5分钟有效）
            _device_cache[cache_key] = config
            return config
            
    except Exception as e:
        logger.error(f"获取设备配置失败: {e}")
    
    # 如果 MCP 不可用，返回默认配置（向后兼容）
    return {
        "ip": AC_IP,
        "token": AC_TOKEN,
        "model": AC_MODEL,
        "name": "空调",
    }


def get_device_connection(device_name: str = DEFAULT_AC_NAME):
    """获取设备连接"""
    config = get_device_config(device_name)
    
    if not config.get("ip") or not config.get("token"):
        raise ValueError(f"设备 {device_name} 配置不完整，缺少 IP 或 Token")
    
    return AirConditioningCompanionMcn02(
        ip=config["ip"],
        token=config["token"]
    )


@tool("get_ac_status", description="获取空调当前状态")
def get_ac_status(device_name: str = DEFAULT_AC_NAME):
    """
    获取设备状态并以 JSON 格式返回
    
    参数:
        device_name: 设备名称，默认为"空调"，可以指定具体的设备名如"客厅空调"
    """
    try:
        config = get_device_config(device_name)
        device = get_device_connection(device_name)
        
        props = device.send("get_prop", ["power", "mode", "tar_temp", "fan_level", "ver_swing", "load_power"])
        status = {
            "device_name": config.get("name", device_name),
            "power": props[0],
            "mode": props[1],
            "target_temperature": props[2],
            "fan_level": props[3],
            "vertical_swing": props[4],
            "load_power": props[5],
            "online": True,
            "model": config.get("model", "unknown"),
            "ip": config.get("ip", ""),
        }
        return json.dumps(status, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取空调状态失败: {e}")
        config = get_device_config(device_name)
        error_status = {
            "error": f"获取设备状态失败: {str(e)}",
            "message": f"请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{config.get('ip', 'unknown')}）\n3. 设备Token是否正确",
            "online": False,
            "model": config.get("model", "unknown")
        }
        return json.dumps(error_status, indent=2, ensure_ascii=False)


class PowerArgs(BaseModel):
    power: bool = Field(..., description="空调电源状态，true 开启，false 关闭")
    device_name: str = Field(default=DEFAULT_AC_NAME, description="设备名称，默认为'空调'")


@tool("set_ac_power", args_schema=PowerArgs, description="开启或关闭空调。power=true 开启，power=false 关闭")
def set_ac_power(power: bool, device_name: str = DEFAULT_AC_NAME):
    """
    设置空调电源状态
    
    参数:
        power: True 开启，False 关闭
        device_name: 设备名称，默认为"空调"
    """
    try:
        config = get_device_config(device_name)
        device = get_device_connection(device_name)
        
        if power:
            device.on()
            return json.dumps({
                "message": f"{config.get('name', device_name)} 已开启",
                "power": True
            }, indent=2, ensure_ascii=False)
        else:
            device.off()
            return json.dumps({
                "message": f"{config.get('name', device_name)} 已关闭",
                "power": False
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空调电源失败: {e}")
        config = get_device_config(device_name)
        error_status = {
            "error": f"设置电源状态失败: {str(e)}",
            "message": f"请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{config.get('ip', 'unknown')}）\n3. 设备Token是否正确",
            "online": False,
            "model": config.get("model", "unknown")
        }
        return json.dumps(error_status, indent=2, ensure_ascii=False)


class TemperatureArgs(BaseModel):
    temperature: int = Field(..., ge=16, le=30, description="目标温度（摄氏度），范围 16-30")
    device_name: str = Field(default=DEFAULT_AC_NAME, description="设备名称，默认为'空调'")


@tool("set_ac_temperature", args_schema=TemperatureArgs, description="设置空调目标温度（16-30℃）")
def set_ac_temperature(temperature: int, device_name: str = DEFAULT_AC_NAME):
    """
    设置空调目标温度
    
    参数:
        temperature: 目标温度（16-30℃）
        device_name: 设备名称，默认为"空调"
    """
    try:
        config = get_device_config(device_name)
        device = get_device_connection(device_name)
        
        # 对于 mcn02，目标温度字段为 tar_temp，对应的设置命令通常为 set_tar_temp
        result = device.send("set_tar_temp", [temperature])
        logger.info(f"{config.get('name', device_name)} 温度已设置为{temperature}℃")
        return json.dumps({
            "message": f"{config.get('name', device_name)} 温度已设置为{temperature}℃",
            "target_temperature": temperature,
            "result": result
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空调温度失败: {e}")
        config = get_device_config(device_name)
        error_status = {
            "error": f"设置温度失败: {str(e)}",
            "message": f"请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{config.get('ip', 'unknown')}）\n3. 设备Token是否正确",
            "online": False,
            "model": config.get("model", "unknown")
        }
        return json.dumps(error_status, indent=2, ensure_ascii=False)


@tool("list_devices", description="查询和列出用户的空调设备信息。当用户询问有哪些空调设备时调用此工具。必须传入 system_user_id 参数。")
def list_devices(system_user_id: int):
    """
    查询和列出用户的空调设备信息（只返回空调相关设备）
    
    当用户询问以下问题时，必须调用此工具：
    - "空调设备信息"
    
    参数:
        system_user_id: 系统用户ID（必传），当前为 1000000001（admin用户）
        
    返回:
        空调设备的详细信息，包括设备名称、型号、IP地址、Token、在线状态等
        
    注意：此工具会自动从数据库读取用户的米家账户凭证，无需用户提供账号密码
    """
    try:
        logger.info(f"准备获取用户 {system_user_id} 的设备列表")
        
        # 1. 预检查：MCP 服务文件是否存在
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        mcp_path = os.path.join(project_root, "mcp", "device_query_mcp.py")
        
        if not os.path.exists(mcp_path):
            logger.error(f"开发错误：MCP 服务文件不存在: {mcp_path}")
            return json.dumps({
                "success": False,
                "message": "请先检查设备查询服务是否启动。"
            }, ensure_ascii=False, indent=2)
        
        # 2. 预检查：MCP 依赖是否已安装
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as e:
            logger.error(f"开发错误：MCP 模块未安装: {e}")
            return json.dumps({
                "success": False,
                "message": "请先检查设备查询服务是否启动。"
            }, ensure_ascii=False, indent=2)
        
        # 3. 调用 MCP 服务
        logger.info(f"✅ 预检查通过，正在通过 MCP 获取设备列表...")
        
        async def get_devices():
            try:
                server_params = StdioServerParameters(
                    command="python",
                    args=[mcp_path],
                )
                
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        
                        result = await session.call_tool(
                            "get_user_devices",
                            arguments={"system_user_id": system_user_id}
                        )
                        
                        return result.content[0].text if hasattr(result, 'content') else str(result)
            except Exception as e:
                logger.error(f"MCP 调用失败: {e}")
                return json.dumps({
                    "success": False,
                    "message": "请先检查设备查询服务是否启动。"
                }, ensure_ascii=False, indent=2)
        
        # 在线程池中需要创建新的事件循环
        try:
            devices_json = asyncio.run(get_devices())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                devices_json = loop.run_until_complete(get_devices())
            finally:
                loop.close()
        
        # 解析结果
        devices_data = json.loads(devices_json)
        
        if devices_data.get("success"):
            all_devices = devices_data.get("devices", [])
            
            # 过滤出空调相关的设备
            # 空调设备通常包含 "acpartner"、"aircondition" 等关键词
            ac_devices = []
            for device in all_devices:
                model = device.get("model", "").lower()
                name = device.get("name", "").lower()
                if "acpartner" in model or "aircondition" in model or "空调" in name or "ac" in name:
                    ac_devices.append(device)
            
            if len(ac_devices) == 0:
                return json.dumps({
                    "success": True,
                    "message": "未找到空调设备",
                    "total_devices": 0,
                    "devices": []
                }, indent=2, ensure_ascii=False)
            
            # 构建友好的输出（只包含空调设备）
            device_list = []
            for i, device in enumerate(ac_devices, 1):
                device_info = {
                    "序号": i,
                    "设备名称": device.get("name", "未命名"),
                    "型号": device.get("model", "未知"),
                    "在线状态": "在线" if device.get("isOnline") else "离线",
                    "IP地址": device.get("localip", "N/A"),
                    "Token": device.get("token", "N/A"),
                    "所属家庭": device.get("home_name", "N/A"),
                }
                device_list.append(device_info)
            
            return json.dumps({
                "success": True,
                "message": f"找到 {len(ac_devices)} 个空调设备",
                "total_devices": len(ac_devices),
                "devices": device_list
            }, indent=2, ensure_ascii=False)
        else:
            # 判断是否是凭证问题
            error_msg = devices_data.get("message", "")
            if "未找到小米账号绑定信息" in error_msg or "未找到" in error_msg:
                return json.dumps({
                    "success": False,
                    "message": "未查询到绑定米家账户的Token，请先绑定米家账户。\n可以通过后端API进行绑定：POST /api/v1/xiaomi/login/start"
                }, indent=2, ensure_ascii=False)
            else:
                return json.dumps({
                    "success": False,
                    "message": error_msg
                }, indent=2, ensure_ascii=False)
        
    except Exception as e:
        error_str = str(e)
        logger.error(f"列出设备失败: {e}")
        
        # 判断错误类型，给出友好提示
        if "Connection refused" in error_str or "timeout" in error_str.lower():
            return json.dumps({
                "success": False,
                "message": "请先开启设备查询MCP服务，无法连接到MCP服务。"
            }, indent=2, ensure_ascii=False)
        elif "No module named" in error_str:
            return json.dumps({
                "success": False,
                "message": f"请先安装MCP所需的依赖模块：{error_str}"
            }, indent=2, ensure_ascii=False)
        else:
            return json.dumps({
                "success": False,
                "message": f"获取设备列表失败：{error_str}"
            }, indent=2, ensure_ascii=False)