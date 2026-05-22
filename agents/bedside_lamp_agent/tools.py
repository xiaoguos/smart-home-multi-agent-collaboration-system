from langchain_core.tools import tool
from miio import Yeelight
import json
import os
import asyncio
import concurrent.futures
from pydantic import BaseModel, Field
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import httpx
from a2a.client import ClientFactory, A2ACardResolver
from a2a.types import Message, Role
from a2a.helpers import new_text_part
from a2a.client.client import ClientConfig
from a2a.client.base_client import SendMessageRequest

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_USER_ID = int(os.getenv("DEFAULT_SYSTEM_USER_ID", "1000000001"))
DEFAULT_LAMP_NAME = os.getenv("LAMP_DEFAULT_NAME", "床头灯")
DATA_MINING_URL = os.getenv("DATA_MINING_URL", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")

_dm_executor = ThreadPoolExecutor(max_workers=2)

MCP_GATEWAY_SSE_URL = os.getenv("MCP_GATEWAY_SSE_URL", "http://127.0.0.1:8099/sse")
MCP_GATEWAY_TOOL = os.getenv("MCP_GATEWAY_PROXY_TOOL", "call_gateway_service_tool")
MCP_DEVICE_SERVICE = os.getenv("MCP_DEVICE_SERVICE_NAME", "device_query")

_device_cache: dict = {}
_device_instances: dict = {}
_instance_lock = threading.Lock()
device_lock = threading.Lock()


async def _call_mcp_gateway(tool_name: str, arguments: dict) -> dict | None:
    """通过 SSE 连接已运行的 MCP 网关调用工具。"""
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
        raise RuntimeError(f"MCP 网关返回失败: {gateway_payload.get('message')}")

    wrapped = gateway_payload.get("result", {})
    parsed = wrapped.get("parsed") if isinstance(wrapped, dict) else None
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except json.JSONDecodeError:
            pass
    return parsed if isinstance(parsed, dict) else None


def _run_async(coro):
    """在同步上下文中安全运行异步协程。"""
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=30)
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


class UserPrefsArgs(BaseModel):
    scene: str = Field(..., description="场景描述，如：睡觉、阅读、起床、看电影、浪漫等")
    user_id: int = Field(default=DEFAULT_SYSTEM_USER_ID, description="系统用户ID")


@tool("query_user_lamp_preferences", args_schema=UserPrefsArgs, description="查询用户在指定场景下的床头灯使用习惯，获取个性化亮度、色温等参数建议")
def query_user_lamp_preferences(scene: str, user_id: int = DEFAULT_SYSTEM_USER_ID) -> str:
    """向数据挖掘Agent查询用户的床头灯习惯偏好，用于个性化控制"""
    if not DATA_MINING_URL:
        return json.dumps({
            "available": False,
            "message": "数据挖掘服务未配置，将使用默认参数",
        }, ensure_ascii=False)

    query = f"查询用户在'{scene}'场景下的床头灯使用习惯，包括亮度、色温偏好和操作规律 (用户ID: {user_id})"
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
        logger.error("query_user_lamp_preferences 异常: %s", e)
        return json.dumps({"available": False, "message": str(e)}, ensure_ascii=False)


def _get_device(device_name: str = DEFAULT_LAMP_NAME, system_user_id: int = DEFAULT_SYSTEM_USER_ID) -> Yeelight:
    """通过 MCP 网关获取设备配置并返回 Yeelight 设备实例（按 ip:token 缓存）。"""
    cache_key = f"{system_user_id}_{device_name}"

    if cache_key not in _device_cache:
        result = _run_async(_call_mcp_gateway(
            "get_device_by_name",
            {"system_user_id": system_user_id, "device_name": device_name},
        ))
        if not result:
            raise RuntimeError(f"MCP 网关未返回设备信息: {device_name}")
        devices = result.get("devices") or []
        if not devices:
            raise RuntimeError(f"用户 {system_user_id} 下未找到设备: {device_name}")
        _device_cache[cache_key] = devices[0]
        logger.info("通过 MCP 网关获取设备配置成功: ip=%s", devices[0].get("localip"))

    info = _device_cache[cache_key]
    ip = info.get("localip", "")
    token = info.get("token", "")

    if not ip or not token:
        raise RuntimeError(f"设备 {device_name} 配置不完整，缺少 IP 或 Token")

    instance_key = f"{ip}:{token}"
    with _instance_lock:
        if instance_key not in _device_instances:
            _device_instances[instance_key] = Yeelight(ip, token)
            logger.info("Yeelight 设备实例创建成功: ip=%s", ip)
    return _device_instances[instance_key]


@tool("get_lamp_status", description="获取床头灯当前状态，包括电源、亮度、色温、颜色等信息")
def get_lamp_status():
    """获取床头灯设备状态并以 JSON 格式返回"""
    try:
        device = _get_device()
        with device_lock:
            s = device.status()
            status = {
                "power": s.power.value if hasattr(s, 'power') else None,
                "is_on": s.is_on if hasattr(s, 'is_on') else None,
                "brightness": s.brightness if hasattr(s, 'brightness') else None,
                "color_temp": s.color_temp if hasattr(s, 'color_temp') else None,
                "color_mode": s.color_mode.value if hasattr(s, 'color_mode') else None,
                "rgb": str(s.rgb) if hasattr(s, 'rgb') else None,
                "online": True,
            }
            return json.dumps(status, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取床头灯状态失败: {e}")
        return json.dumps({"error": str(e), "online": False}, indent=2, ensure_ascii=False)


class PowerArgs(BaseModel):
    power: bool = Field(..., description="床头灯电源状态，true 开启，false 关闭")


@tool("set_lamp_power", args_schema=PowerArgs, description="开启或关闭床头灯。power=true 开启，power=false 关闭")
def set_lamp_power(power: bool):
    """开启或关闭床头灯"""
    try:
        device = _get_device()
        with device_lock:
            result = device.on() if power else device.off()
            action = "开启" if power else "关闭"
            logger.info(f"床头灯已{action}")
            return json.dumps({"message": f"床头灯已{action}", "power": power, "result": str(result)}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置床头灯电源失败: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


class BrightnessArgs(BaseModel):
    brightness: int = Field(..., ge=1, le=100, description="亮度值，范围 1-100")


@tool("set_lamp_brightness", args_schema=BrightnessArgs, description="设置床头灯亮度（1-100）")
def set_lamp_brightness(brightness: int):
    """设置床头灯亮度"""
    try:
        device = _get_device()
        with device_lock:
            result = device.set_brightness(brightness)
            logger.info(f"亮度已设置为{brightness}%")
            return json.dumps({"message": f"亮度已设置为{brightness}%", "brightness": brightness, "result": str(result)}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置床头灯亮度失败: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


class ColorTempArgs(BaseModel):
    color_temp: int = Field(..., ge=1700, le=6500, description="色温值，范围 1700-6500K")


@tool("set_lamp_color_temp", args_schema=ColorTempArgs, description="设置床头灯色温（1700-6500K，暖光到冷光）")
def set_lamp_color_temp(color_temp: int):
    """设置床头灯色温"""
    try:
        device = _get_device()
        with device_lock:
            result = device.set_color_temp(color_temp)
            temp_desc = "暖光" if color_temp < 3000 else "中性光" if color_temp < 5000 else "冷光"
            logger.info(f"色温已设置为{color_temp}K ({temp_desc})")
            return json.dumps({"message": f"色温已设置为{color_temp}K ({temp_desc})", "color_temp": color_temp, "description": temp_desc, "result": str(result)}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置床头灯色温失败: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


class ColorArgs(BaseModel):
    red: int = Field(..., ge=0, le=255, description="红色值，范围 0-255")
    green: int = Field(..., ge=0, le=255, description="绿色值，范围 0-255")
    blue: int = Field(..., ge=0, le=255, description="蓝色值，范围 0-255")


@tool("set_lamp_color", args_schema=ColorArgs, description="设置床头灯RGB颜色（红、绿、蓝各0-255）")
def set_lamp_color(red: int, green: int, blue: int):
    """设置床头灯RGB颜色"""
    try:
        device = _get_device()
        with device_lock:
            result = device.set_rgb((red, green, blue))
            logger.info(f"颜色已设置为 RGB({red}, {green}, {blue})")
            return json.dumps({"message": f"颜色已设置为 RGB({red}, {green}, {blue})", "red": red, "green": green, "blue": blue, "color_hex": f"#{red:02x}{green:02x}{blue:02x}", "result": str(result)}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置床头灯颜色失败: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


class SceneArgs(BaseModel):
    scene: str = Field(..., description="场景名称: 'reading' (阅读), 'sleep' (睡眠), 'romantic' (浪漫), 'night' (夜灯)")


@tool("set_lamp_scene", args_schema=SceneArgs, description="设置床头灯预设场景（阅读/睡眠/浪漫/夜灯）")
def set_lamp_scene(scene: str):
    """设置床头灯预设场景"""
    scenes = {
        "reading": {"brightness": 100, "color_temp": 4000, "desc": "阅读模式：100%亮度，4000K中性光"},
        "sleep": {"brightness": 10, "color_temp": 2000, "desc": "睡眠模式：10%亮度，2000K暖光"},
        "romantic": {"brightness": 30, "rgb": (255, 100, 100), "desc": "浪漫模式：30%亮度，粉红色"},
        "night": {"brightness": 5, "color_temp": 1700, "desc": "夜灯模式：5%亮度，1700K极暖光"},
    }

    if scene not in scenes:
        return json.dumps({"error": f"未知场景: {scene}", "available_scenes": list(scenes.keys())}, indent=2, ensure_ascii=False)

    try:
        device = _get_device()
        with device_lock:
            cfg = scenes[scene]
            device.set_brightness(cfg["brightness"])
            if "color_temp" in cfg:
                device.set_color_temp(cfg["color_temp"])
            elif "rgb" in cfg:
                r, g, b = cfg["rgb"]
                device.set_rgb((r, g, b))
            logger.info(f"场景已设置为: {scene}")
            return json.dumps({"message": f"场景已设置为: {scene}", "scene": scene, "description": cfg["desc"]}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置床头灯场景失败: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


class RecordOperationArgs(BaseModel):
    action: str = Field(..., description="执行的操作，如：turn_on, turn_off, set_brightness, set_color_temp, set_color, set_scene")
    parameters: dict = Field(default_factory=dict, description="操作参数，如 {brightness: 50} 或 {color_temp: 3200}")
    success: bool = Field(..., description="操作是否成功")
    response: str = Field(default="", description="操作响应描述")
    error_message: str = Field(default="", description="失败时的错误信息")
    execution_time: int = Field(default=0, description="执行耗时（毫秒）")
    user_id: int = Field(default=DEFAULT_SYSTEM_USER_ID, description="系统用户ID")
    context_id: str = Field(default="", description="会话上下文ID")


@tool("record_device_operation", args_schema=RecordOperationArgs, description="将床头灯操作记录到数据库，每次成功控制设备后必须调用此工具记录操作，以便系统学习用户习惯")
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
            "device_type": "bedside_lamp",
            "device_name": DEFAULT_LAMP_NAME,
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
