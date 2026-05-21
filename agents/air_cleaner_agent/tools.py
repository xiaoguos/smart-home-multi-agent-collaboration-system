from langchain_core.tools import tool
from miio.miot_device import MiotDevice
from miio.integrations.airpurifier.zhimi.airpurifier_miot import AirPurifierMiot
import json
import os
import asyncio
import concurrent.futures
from pydantic import BaseModel, Field
import logging
import threading

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_USER_ID = int(os.getenv("DEFAULT_SYSTEM_USER_ID", "1000000001"))
DEFAULT_PURIFIER_NAME = os.getenv("PURIFIER_DEFAULT_NAME", "空气净化器")

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


def _get_device_instances(device_name: str = DEFAULT_PURIFIER_NAME, system_user_id: int = DEFAULT_SYSTEM_USER_ID) -> tuple[AirPurifierMiot, MiotDevice]:
    """通过 MCP 网关获取设备配置并返回设备实例（按 ip:token 缓存）。"""
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
    model = info.get("model", "")

    if not ip or not token:
        raise RuntimeError(f"设备 {device_name} 配置不完整，缺少 IP 或 Token")

    instance_key = f"{ip}:{token}"
    with _instance_lock:
        if instance_key not in _device_instances:
            _device_instances[instance_key] = (
                AirPurifierMiot(ip, token),
                MiotDevice(ip=ip, token=token, model=model),
            )
    return _device_instances[instance_key]


@tool("get_purifier_status", description="获取空气净化器当前状态，包括电源、PM2.5、湿度、风扇等级、工作模式、滤芯寿命等信息")
def get_purifier_status():
    """获取空气净化器设备状态并以 JSON 格式返回"""
    try:
        purifier_dev, miot_dev = _get_device_instances()
        with device_lock:
            status_obj = purifier_dev.status()
            if hasattr(status_obj, 'data'):
                status_data = status_obj.data
                status_data['online'] = True
                status_data['model'] = miot_dev.model
                return json.dumps(status_data, indent=2, ensure_ascii=False, default=str)
            else:
                logger.warning("设备状态对象没有 data 属性，使用降级方案")
                power = miot_dev.get_property_by(2, 1)
                fan_level = miot_dev.get_property_by(2, 5)
                led = miot_dev.get_property_by(2, 6)
                return json.dumps({
                    "power": power[0].get('value') if isinstance(power, list) and power else power,
                    "fan_level": fan_level[0].get('value') if isinstance(fan_level, list) and fan_level else fan_level,
                    "led_brightness": led[0].get('value') if isinstance(led, list) and led else led,
                    "online": True,
                    "model": miot_dev.model,
                }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取空气净化器状态失败: {e}")
        return json.dumps({"error": str(e), "online": False}, indent=2, ensure_ascii=False)


class PowerArgs(BaseModel):
    power: bool = Field(..., description="空气净化器电源状态，true 开启，false 关闭")


@tool("set_purifier_power", args_schema=PowerArgs, description="开启或关闭空气净化器。power=true 开启，power=false 关闭")
def set_purifier_power(power: bool):
    """开启或关闭空气净化器"""
    try:
        _, miot_dev = _get_device_instances()
        with device_lock:
            result = miot_dev.set_property_by(2, 1, power)
            action = "开启" if power else "关闭"
            logger.info(f"空气净化器已{action}")
            return json.dumps({"message": f"空气净化器已{action}", "power": power, "result": str(result)}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器电源失败: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


class ModeArgs(BaseModel):
    mode: int = Field(..., ge=0, le=2, description="工作模式：0=自动模式，1=睡眠模式，2=手动模式")


@tool("set_purifier_mode", args_schema=ModeArgs, description="设置空气净化器工作模式（0=自动，1=睡眠，2=手动）")
def set_purifier_mode(mode: int):
    """设置空气净化器工作模式"""
    try:
        _, miot_dev = _get_device_instances()
        with device_lock:
            result = miot_dev.set_property_by(2, 4, mode)
            mode_names = {0: "自动模式", 1: "睡眠模式", 2: "手动模式"}
            mode_name = mode_names.get(mode, f"模式{mode}")
            logger.info(f"工作模式已设置为{mode_name}")
            return json.dumps({"message": f"工作模式已设置为{mode_name}", "mode": mode, "mode_name": mode_name, "result": str(result)}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器工作模式失败: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


class FanLevelArgs(BaseModel):
    level: int = Field(..., ge=1, le=4, description="风扇等级，范围 1-4 (1档、2档、3档、4档)")


@tool("set_purifier_fan_level", args_schema=FanLevelArgs, description="设置空气净化器风扇等级（1档、2档、3档、4档）")
def set_purifier_fan_level(level: int):
    """设置空气净化器风扇等级

    注意：要手动设置风扇等级，设备必须处于手动模式（mode=2）。
    如果设备处于自动模式，会自动先切换到手动模式。
    """
    try:
        _, miot_dev = _get_device_instances()
        with device_lock:
            try:
                current_mode_result = miot_dev.get_property_by(2, 4)
                current_mode = current_mode_result[0].get('value') if isinstance(current_mode_result, list) else current_mode_result
                if current_mode != 2:
                    logger.info(f"当前为模式{current_mode}，切换到手动模式")
                    miot_dev.set_property_by(2, 4, 2)
            except Exception as mode_error:
                logger.warning(f"切换模式时出错，继续尝试设置风扇等级: {mode_error}")
            result = miot_dev.set_property_by(2, 5, level)
            logger.info(f"风扇等级已设置为{level}档")
            return json.dumps({"message": f"风扇等级已设置为{level}档", "fan_level": level, "result": str(result)}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器风扇等级失败: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


class LEDBrightnessArgs(BaseModel):
    brightness: bool = Field(..., description="LED按键亮度开关，true 开启，false 关闭")


@tool("set_purifier_led", args_schema=LEDBrightnessArgs, description="设置空气净化器LED按键亮度开关")
def set_purifier_led(brightness: bool):
    """设置空气净化器LED按键亮度"""
    try:
        _, miot_dev = _get_device_instances()
        with device_lock:
            result = miot_dev.set_property_by(2, 6, brightness)
            status = "开启" if brightness else "关闭"
            logger.info(f"LED亮度已{status}")
            return json.dumps({"message": f"LED亮度已{status}", "led_brightness": brightness, "result": str(result)}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器LED失败: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


class AlarmArgs(BaseModel):
    alarm: bool = Field(..., description="提示音开关，true 开启，false 关闭")


@tool("set_purifier_alarm", args_schema=AlarmArgs, description="设置空气净化器提示音开关")
def set_purifier_alarm(alarm: bool):
    """设置空气净化器提示音"""
    try:
        _, miot_dev = _get_device_instances()
        with device_lock:
            result = miot_dev.set_property_by(2, 7, alarm)
            status = "开启" if alarm else "关闭"
            logger.info(f"提示音已{status}")
            return json.dumps({"message": f"提示音已{status}", "alarm": alarm, "result": str(result)}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器提示音失败: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


class ChildLockArgs(BaseModel):
    child_lock: bool = Field(..., description="童锁开关，true 开启，false 关闭")


@tool("set_purifier_child_lock", args_schema=ChildLockArgs, description="设置空气净化器童锁（物理控制锁）")
def set_purifier_child_lock(child_lock: bool):
    """设置空气净化器童锁"""
    try:
        _, miot_dev = _get_device_instances()
        with device_lock:
            result = miot_dev.set_property_by(2, 9, child_lock)
            status = "开启" if child_lock else "关闭"
            logger.info(f"童锁已{status}")
            return json.dumps({"message": f"童锁已{status}", "child_lock": child_lock, "result": str(result)}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器童锁失败: {e}")
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


class ListDevicesArgs(BaseModel):
    system_user_id: int = Field(..., description="系统用户ID，用于查询该用户下的所有空气净化器设备")


@tool("list_devices", args_schema=ListDevicesArgs, description="查询和列出用户的空气净化器设备信息。当用户询问有哪些空气净化器设备时调用此工具。必须传入 system_user_id 参数。")
def list_devices(system_user_id: int):
    """列出用户的空气净化器设备"""
    try:
        result = _run_async(_call_mcp_gateway(
            "get_user_devices",
            {"system_user_id": system_user_id},
        ))
        if not result:
            raise RuntimeError("MCP 网关未返回设备列表")
        devices = result.get("devices") or []
        return json.dumps({"devices": devices, "total": len(devices)}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("查询设备列表失败: %s", e)
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)
