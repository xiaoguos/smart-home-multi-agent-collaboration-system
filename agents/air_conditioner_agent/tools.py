from langchain_core.tools import tool
from miio import AirConditioningCompanionMcn02
import json
from pydantic import BaseModel, Field
import logging
import asyncio
import concurrent.futures
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import httpx
from a2a.client import ClientFactory, A2ACardResolver
from a2a.types import Message, Role
from a2a.helpers import new_text_part
from a2a.client.client import ClientConfig
from a2a.client.base_client import SendMessageRequest

logger = logging.getLogger(__name__)

# 默认配置 - 从 .env 读取，MCP 不可用时作为回退值
DEFAULT_SYSTEM_USER_ID = int(os.getenv("DEFAULT_SYSTEM_USER_ID", "1000000001"))
DEFAULT_AC_NAME = os.getenv("AC_DEFAULT_NAME", "空调")
DATA_MINING_URL = os.getenv("DATA_MINING_URL", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")

_dm_executor = ThreadPoolExecutor(max_workers=2)
AC_IP = os.getenv("AC_IP", "192.168.110.129")
AC_TOKEN = os.getenv("AC_TOKEN", "1724bf8d57b355173dfa08ae23367f86")
AC_MODEL = os.getenv("AC_MODEL", "lumi.acpartner.mcn02")

# MCP 网关地址（连接已运行的网关，不启动子进程）
MCP_GATEWAY_SSE_URL = os.getenv("MCP_GATEWAY_SSE_URL", "http://127.0.0.1:8099/sse")
MCP_GATEWAY_TOOL = os.getenv("MCP_GATEWAY_PROXY_TOOL", "call_gateway_service_tool")
MCP_DEVICE_SERVICE = os.getenv("MCP_DEVICE_SERVICE_NAME", "device_query")

# 设备缓存（避免频繁查询）
_device_cache = {}


async def _call_mcp_gateway(tool_name: str, arguments: dict) -> dict | None:
    """通过 SSE 连接已运行的 MCP 网关调用工具。"""
    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        gateway_args = {
            "service_name": MCP_DEVICE_SERVICE,
            "tool_name": tool_name,
            "arguments_json": json.dumps(arguments, ensure_ascii=False),
        }
        async with sse_client(MCP_GATEWAY_SSE_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(MCP_GATEWAY_TOOL, arguments=gateway_args)

        text = ""
        if hasattr(result, "content") and result.content:
            text = getattr(result.content[0], "text", "") or ""
        if not text:
            return None

        gateway_payload = json.loads(text)
        if not gateway_payload.get("success"):
            logger.warning("MCP 网关返回失败: %s", gateway_payload.get("message"))
            return None

        wrapped = gateway_payload.get("result", {})
        parsed = wrapped.get("parsed") if isinstance(wrapped, dict) else None
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except json.JSONDecodeError:
                pass
        return parsed if isinstance(parsed, dict) else None

    except Exception as e:
        logger.error("通过 MCP 网关调用工具失败: tool=%s, error=%s", tool_name, e)
        return None


def _run_async(coro):
    """在同步上下文中安全运行异步协程（兼容已有事件循环的情况）。"""
    try:
        asyncio.get_running_loop()
        # 当前线程已有事件循环，用独立线程运行
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=30)
    except RuntimeError:
        return asyncio.run(coro)


async def _call_data_mining_async(query: str, timeout: float = 30.0) -> dict:
    """通过 A2A 协议向数据挖掘Agent查询用户偏好。"""
    if not DATA_MINING_URL:
        return {"success": False, "error": "DATA_MINING_URL 未配置"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resolver = A2ACardResolver(httpx_client=client, base_url=DATA_MINING_URL)
            agent_card = await resolver.get_agent_card()
            config = ClientConfig(
                streaming=False,
                polling=False,
                httpx_client=client,
                supported_protocol_bindings=["JSONRPC"],
                use_client_preference=False,
                accepted_output_modes=["text", "text/plain"],
            )
            factory = ClientFactory(config=config)
            a2a_client = factory.create(card=agent_card)
            message = Message(
                context_id=str(uuid4()),
                role=Role.ROLE_USER,
                parts=[new_text_part(query)],
                message_id=uuid4().hex,
            )
            request = SendMessageRequest()
            request.message.CopyFrom(message)
            final_content = ""
            async for response in a2a_client.send_message(request):
                if hasattr(response, "artifacts") and response.artifacts:
                    for artifact in response.artifacts:
                        if hasattr(artifact, "parts"):
                            for part in artifact.parts:
                                if hasattr(part, "root") and hasattr(part.root, "text"):
                                    final_content = part.root.text
                if not final_content and hasattr(response, "message"):
                    msg = response.message
                    if hasattr(msg, "parts") and msg.parts:
                        for part in msg.parts:
                            if hasattr(part, "text"):
                                final_content = part.text
                            elif hasattr(part, "root") and hasattr(part.root, "text"):
                                final_content = part.root.text
            return {"success": True, "content": final_content}
    except Exception as e:
        logger.error("调用数据挖掘Agent失败: %s", e)
        return {"success": False, "error": str(e)}


def _run_data_mining(query: str, timeout: float = 30.0) -> dict:
    """在独立线程中运行数据挖掘A2A调用，避免事件循环冲突。"""
    def run_in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_call_data_mining_async(query, timeout))
        finally:
            loop.close()

    future = _dm_executor.submit(run_in_new_loop)
    return future.result(timeout=timeout + 5)


class UserACPrefsArgs(BaseModel):
    scene: str = Field(..., description="场景描述，如：睡觉、起床、运动后、回家、工作等")
    user_id: int = Field(default=DEFAULT_SYSTEM_USER_ID, description="系统用户ID")


@tool("query_user_ac_preferences", args_schema=UserACPrefsArgs, description="查询用户在指定场景下的空调使用习惯，获取个性化温度、模式等参数建议")
def query_user_ac_preferences(scene: str, user_id: int = DEFAULT_SYSTEM_USER_ID) -> str:
    """向数据挖掘Agent查询用户的空调使用习惯偏好，用于个性化控制"""
    if not DATA_MINING_URL:
        return json.dumps({
            "available": False,
            "message": "数据挖掘服务未配置，将使用默认参数",
        }, ensure_ascii=False)

    query = f"查询用户在'{scene}'场景下的空调使用习惯，包括温度偏好、模式偏好和操作规律 (用户ID: {user_id})"
    try:
        result = _run_data_mining(query)
        if result.get("success"):
            content = result.get("content", "")
            return content if content else json.dumps({"available": False, "message": "暂无该场景的历史数据"}, ensure_ascii=False)
        else:
            return json.dumps({
                "available": False,
                "message": f"数据挖掘查询失败: {result.get('error')}",
                "fallback": "将使用默认参数",
            }, ensure_ascii=False)
    except Exception as e:
        logger.error("query_user_ac_preferences 异常: %s", e)
        return json.dumps({"available": False, "message": str(e)}, ensure_ascii=False)


async def get_device_info_from_mcp(system_user_id: int, device_name: str = "空调") -> dict | None:
    """通过已运行的 MCP 网关查询指定名称的设备信息。"""
    logger.info("正在通过 MCP 网关查询设备: %s", device_name)
    result = await _call_mcp_gateway(
        "get_device_by_name",
        {"system_user_id": system_user_id, "device_name": device_name},
    )
    if not result:
        return None
    devices = result.get("devices") or []
    return devices[0] if devices else None


def get_device_config(device_name: str = DEFAULT_AC_NAME, system_user_id: int = DEFAULT_SYSTEM_USER_ID) -> dict:
    """获取设备配置（优先通过 MCP 网关，失败则使用缓存或 .env 默认配置）。"""
    cache_key = f"{system_user_id}_{device_name}"

    if cache_key in _device_cache:
        logger.info("使用缓存的设备信息: %s", device_name)
        return _device_cache[cache_key]

    try:
        device_info = _run_async(get_device_info_from_mcp(system_user_id, device_name))
        if device_info:
            config = {
                "ip": device_info.get("localip", ""),
                "token": device_info.get("token", ""),
                "model": device_info.get("model", ""),
                "name": device_info.get("name", device_name),
                "did": device_info.get("did", ""),
                "isOnline": device_info.get("isOnline", False),
            }
            _device_cache[cache_key] = config
            return config
    except Exception as e:
        logger.error("获取设备配置失败: %s", e)

    return {
        "ip": AC_IP,
        "token": AC_TOKEN,
        "model": AC_MODEL,
        "name": "空调",
    }


def get_device_connection(device_name: str = DEFAULT_AC_NAME):
    """获取设备连接。"""
    config = get_device_config(device_name)
    if not config.get("ip") or not config.get("token"):
        raise ValueError(f"设备 {device_name} 配置不完整，缺少 IP 或 Token")
    return AirConditioningCompanionMcn02(
        ip=config["ip"],
        token=config["token"],
        model=config.get("model") or AC_MODEL,
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
        logger.error("获取空调状态失败: %s", e)
        config = get_device_config(device_name)
        return json.dumps({
            "error": f"获取设备状态失败: {str(e)}",
            "message": f"请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前：{config.get('ip', 'unknown')}）\n3. 设备Token是否正确",
            "online": False,
            "model": config.get("model", "unknown"),
        }, indent=2, ensure_ascii=False)


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
            return json.dumps({"message": f"{config.get('name', device_name)} 已开启", "power": True}, indent=2, ensure_ascii=False)
        else:
            device.off()
            return json.dumps({"message": f"{config.get('name', device_name)} 已关闭", "power": False}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("设置空调电源失败: %s", e)
        config = get_device_config(device_name)
        return json.dumps({
            "error": f"设置电源状态失败: {str(e)}",
            "message": f"请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前：{config.get('ip', 'unknown')}）\n3. 设备Token是否正确",
            "online": False,
            "model": config.get("model", "unknown"),
        }, indent=2, ensure_ascii=False)


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
        result = device.send("set_tar_temp", [temperature])
        logger.info("%s 温度已设置为%d℃", config.get("name", device_name), temperature)
        return json.dumps({
            "message": f"{config.get('name', device_name)} 温度已设置为{temperature}℃",
            "target_temperature": temperature,
            "result": result,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("设置空调温度失败: %s", e)
        config = get_device_config(device_name)
        return json.dumps({
            "error": f"设置温度失败: {str(e)}",
            "message": f"请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前：{config.get('ip', 'unknown')}）\n3. 设备Token是否正确",
            "online": False,
            "model": config.get("model", "unknown"),
        }, indent=2, ensure_ascii=False)


@tool("list_devices", description="查询和列出用户的空调设备信息。当用户询问有哪些空调设备时调用此工具。必须传入 system_user_id 参数。")
def list_devices(system_user_id: int):
    """
    查询用户的空调设备信息（通过 MCP 网关获取所有设备后过滤出空调相关设备）

    参数:
        system_user_id: 系统用户ID（必传）
    """
    try:
        logger.info("准备通过 MCP 网关获取用户 %d 的设备列表", system_user_id)
        result = _run_async(
            _call_mcp_gateway("get_user_devices", {"system_user_id": system_user_id})
        )

        if not result:
            return json.dumps({
                "success": False,
                "message": "MCP 网关未返回数据，请确认 MCP 网关（端口 8099）已启动。",
            }, indent=2, ensure_ascii=False)

        if not result.get("success"):
            error_msg = result.get("message", "")
            if "未找到" in error_msg or "绑定" in error_msg:
                return json.dumps({
                    "success": False,
                    "message": "未查询到绑定米家账户的 Token，请先绑定米家账户。",
                }, indent=2, ensure_ascii=False)
            return json.dumps({"success": False, "message": error_msg}, indent=2, ensure_ascii=False)

        all_devices = result.get("devices") or []
        ac_devices = [
            d for d in all_devices
            if "acpartner" in d.get("model", "").lower()
            or "aircondition" in d.get("model", "").lower()
            or "空调" in d.get("name", "").lower()
            or "ac" in d.get("name", "").lower()
        ]

        if not ac_devices:
            return json.dumps({"success": True, "message": "未找到空调设备", "total_devices": 0, "devices": []}, indent=2, ensure_ascii=False)

        device_list = [
            {
                "序号": i,
                "设备名称": d.get("name", "未命名"),
                "型号": d.get("model", "未知"),
                "在线状态": "在线" if d.get("isOnline") else "离线",
                "IP地址": d.get("localip", "N/A"),
                "Token": d.get("token", "N/A"),
                "所属家庭": d.get("home_name", "N/A"),
            }
            for i, d in enumerate(ac_devices, 1)
        ]
        return json.dumps({
            "success": True,
            "message": f"找到 {len(ac_devices)} 个空调设备",
            "total_devices": len(ac_devices),
            "devices": device_list,
        }, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error("列出设备失败: %s", e)
        return json.dumps({"success": False, "message": f"获取设备列表失败：{e}"}, indent=2, ensure_ascii=False)


class RecordACOperationArgs(BaseModel):
    action: str = Field(..., description="执行的操作，如：turn_on, turn_off, set_temperature")
    parameters: dict = Field(default_factory=dict, description="操作参数，如 {temperature: 26} 或 {power: true}")
    success: bool = Field(..., description="操作是否成功")
    response: str = Field(default="", description="操作响应描述")
    error_message: str = Field(default="", description="失败时的错误信息")
    execution_time: int = Field(default=0, description="执行耗时（毫秒）")
    user_id: int = Field(default=DEFAULT_SYSTEM_USER_ID, description="系统用户ID")
    context_id: str = Field(default="", description="会话上下文ID")


@tool("record_device_operation", args_schema=RecordACOperationArgs, description="将空调操作记录到数据库，每次成功控制设备后必须调用此工具记录操作，以便系统学习用户习惯")
def record_device_operation(
    action: str,
    parameters: dict,
    success: bool,
    response: str = "",
    error_message: str = "",
    execution_time: int = 0,
    user_id: int = DEFAULT_SYSTEM_USER_ID,
    context_id: str = "",
) -> str:
    """将设备操作记录上报到后端数据库，供数据挖掘Agent学习用户习惯"""
    try:
        payload = {
            "system_user_id": user_id,
            "context_id": context_id or None,
            "device_type": "air_conditioner",
            "device_name": DEFAULT_AC_NAME,
            "action": action,
            "parameters": parameters,
            "success": success,
            "response": response or None,
            "error_message": error_message or None,
            "execution_time": execution_time or None,
        }
        resp = httpx.post(
            f"{BACKEND_URL}/api/v1/device_operations/save",
            json=payload,
            timeout=10.0,
        )
        resp.raise_for_status()
        logger.info("操作记录已上报: action=%s, success=%s", action, success)
        return json.dumps({"recorded": True, "action": action}, ensure_ascii=False)
    except Exception as e:
        logger.warning("操作记录上报失败（不影响设备控制）: %s", e)
        return json.dumps({"recorded": False, "error": str(e)}, ensure_ascii=False)
