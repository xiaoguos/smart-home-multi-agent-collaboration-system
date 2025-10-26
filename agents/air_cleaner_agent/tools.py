from langchain_core.tools import tool
from miio.miot_device import MiotDevice
import json
from pydantic import BaseModel, Field
import time
import logging
import threading

# 配置日志
logger = logging.getLogger(__name__)

# 设备配置
PURIFIER_IP = "192.168.110.120"
PURIFIER_TOKEN = "569905df67a11d6b67a575097255c798"
PURIFIER_MODEL = "zhimi.airp.oa1"

# 创建单个设备实例
device = MiotDevice(
    ip=PURIFIER_IP,
    token=PURIFIER_TOKEN,
    model=PURIFIER_MODEL
)

# 添加线程锁，确保同一时间只有一个操作
device_lock = threading.Lock()

def safe_call(func, *args):
    """
    安全调用设备方法，不进行重试
    如果失败，直接抛出异常
    """
    try:
        result = func(*args)
        time.sleep(0.2)  # 稍微等待一下，避免连续请求
        return result
    except Exception as e:
        logger.error(f"操作失败: {e}")
        raise e


@tool("get_purifier_status", description="获取空气净化器当前状态，包括电源、PM2.5、湿度、风扇等级、工作模式、滤芯寿命等信息")
def get_purifier_status():
    """获取空气净化器设备状态并以 JSON 格式返回"""
    try:
        with device_lock:  # 使用锁确保串行执行
            # 一次性获取所有属性，避免重复调用
            power = safe_call(device.get_property_by, 2, 1)
            fan_level = safe_call(device.get_property_by, 2, 2)
            mode = safe_call(device.get_property_by, 2, 3)
            humidity = safe_call(device.get_property_by, 3, 1)
            pm25 = safe_call(device.get_property_by, 3, 6)
            filter_life_level = safe_call(device.get_property_by, 4, 1)
            filter_left_time = safe_call(device.get_property_by, 4, 3)
            child_lock = safe_call(device.get_property_by, 5, 1)
            led_brightness = safe_call(device.get_property_by, 6, 1)
            buzzer = safe_call(device.get_property_by, 7, 1)
            
            status = {
                "power": power[0] if isinstance(power, list) else power,
                "fan_level": fan_level[0] if isinstance(fan_level, list) else fan_level,
                "mode": mode[0] if isinstance(mode, list) else mode,
                "humidity": humidity[0] if isinstance(humidity, list) else humidity,
                "pm25": pm25[0] if isinstance(pm25, list) else pm25,
                "filter_life_level": filter_life_level[0] if isinstance(filter_life_level, list) else filter_life_level,
                "filter_left_time": filter_left_time[0] if isinstance(filter_left_time, list) else filter_left_time,
                "child_lock": child_lock[0] if isinstance(child_lock, list) else child_lock,
                "led_brightness": led_brightness[0] if isinstance(led_brightness, list) else led_brightness,
                "buzzer": buzzer[0] if isinstance(buzzer, list) else buzzer,
                "online": True,
                "model": PURIFIER_MODEL
            }
            return json.dumps(status, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取空气净化器状态失败: {e}")
        error_status = {
            "error": f"获取设备状态失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=PURIFIER_IP),
            "online": False,
            "model": PURIFIER_MODEL
        }
        return json.dumps(error_status, indent=2, ensure_ascii=False)


class PowerArgs(BaseModel):
    power: bool = Field(..., description="空气净化器电源状态，true 开启，false 关闭")


@tool("set_purifier_power", args_schema=PowerArgs, description="开启或关闭空气净化器。power=true 开启，power=false 关闭")
def set_purifier_power(power: bool):
    """开启或关闭空气净化器"""
    try:
        with device_lock:  # 使用锁确保串行执行
            result = safe_call(device.set_property_by, 2, 1, power)
            action = "开启" if power else "关闭"
            logger.info(f"空气净化器已{action}")
            return json.dumps({
                "message": f"空气净化器已{action}",
                "power": power,
                "result": str(result)
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器电源失败: {e}")
        return json.dumps({
            "error": f"设置电源状态失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=PURIFIER_IP),
            "online": False,
            "model": PURIFIER_MODEL
        }, indent=2, ensure_ascii=False)


class FanLevelArgs(BaseModel):
    level: int = Field(..., ge=1, le=3, description="风扇等级，范围 1-3 (1=低速, 2=中速, 3=高速)")


@tool("set_purifier_fan_level", args_schema=FanLevelArgs, description="设置空气净化器风扇等级（1=低速，2=中速，3=高速）")
def set_purifier_fan_level(level: int):
    """设置空气净化器风扇等级"""
    try:
        with device_lock:
            result = safe_call(device.set_property_by, 2, 2, level)
            level_name = {1: "低速", 2: "中速", 3: "高速"}[level]
            logger.info(f"风扇等级已设置为{level_name}")
            return json.dumps({
                "message": f"风扇等级已设置为{level_name}",
                "fan_level": level,
                "result": str(result)
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器风扇等级失败: {e}")
        return json.dumps({
            "error": f"设置风扇等级失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=PURIFIER_IP),
            "online": False,
            "model": PURIFIER_MODEL
        }, indent=2, ensure_ascii=False)


class ModeArgs(BaseModel):
    mode: int = Field(..., ge=0, le=2, description="工作模式，0=自动模式，1=睡眠模式，2=喜爱模式")


@tool("set_purifier_mode", args_schema=ModeArgs, description="设置空气净化器工作模式（0=自动，1=睡眠，2=喜爱）")
def set_purifier_mode(mode: int):
    """设置空气净化器工作模式"""
    try:
        with device_lock:
            result = safe_call(device.set_property_by, 2, 3, mode)
            mode_name = {0: "自动模式", 1: "睡眠模式", 2: "喜爱模式"}[mode]
            logger.info(f"工作模式已设置为{mode_name}")
            return json.dumps({
                "message": f"工作模式已设置为{mode_name}",
                "mode": mode,
                "result": str(result)
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器工作模式失败: {e}")
        return json.dumps({
            "error": f"设置工作模式失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=PURIFIER_IP),
            "online": False,
            "model": PURIFIER_MODEL
        }, indent=2, ensure_ascii=False)


class LEDBrightnessArgs(BaseModel):
    brightness: int = Field(..., ge=0, le=2, description="LED亮度，0=关闭，1=暗，2=亮")


@tool("set_purifier_led", args_schema=LEDBrightnessArgs, description="设置空气净化器LED指示灯亮度（0=关闭，1=暗，2=亮）")
def set_purifier_led(brightness: int):
    """设置空气净化器LED亮度"""
    try:
        with device_lock:
            result = safe_call(device.set_property_by, 6, 1, brightness)
            brightness_name = {0: "关闭", 1: "暗", 2: "亮"}[brightness]
            logger.info(f"LED已设置为{brightness_name}")
            return json.dumps({
                "message": f"LED已设置为{brightness_name}",
                "led_brightness": brightness,
                "result": str(result)
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器LED失败: {e}")
        return json.dumps({
            "error": f"设置LED亮度失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=PURIFIER_IP),
            "online": False,
            "model": PURIFIER_MODEL
        }, indent=2, ensure_ascii=False)