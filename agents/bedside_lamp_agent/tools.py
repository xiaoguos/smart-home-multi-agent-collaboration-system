from langchain_core.tools import tool
from miio import DeviceFactory
from miio.miot_device import MiotDevice
import json
from pydantic import BaseModel, Field
import time
import logging
import threading

# 配置日志
logger = logging.getLogger(__name__)

# 设备配置
LAMP_IP = "192.168.110.129"
LAMP_TOKEN = "4a90f98aaa1273ca34685d66d6e13958"
LAMP_MODEL = "yeelink.light.bslamp2"

# 创建设备实例 - 使用 DeviceFactory 自动检测设备类型（参考 Iot.py）
try:
    device = DeviceFactory.create(LAMP_IP, LAMP_TOKEN)
    logger.info(f"使用 DeviceFactory 创建设备成功: {LAMP_MODEL}")
except Exception as e:
    logger.warning(f"DeviceFactory 创建失败，使用 MiotDevice: {e}")
    device = MiotDevice(
        ip=LAMP_IP,
        token=LAMP_TOKEN,
        model=LAMP_MODEL
    )

# 添加线程锁，确保同一时间只有一个操作
device_lock = threading.Lock()


@tool("get_lamp_status", description="获取床头灯当前状态，包括电源、亮度、色温、颜色等信息")
def get_lamp_status():
    """获取床头灯设备状态并以 JSON 格式返回"""
    try:
        with device_lock:  # 使用锁确保串行执行
            # 参考 Iot.py - 使用 MIoT 协议获取属性
            # siid=2 (灯光服务), piid=1-5 (各种属性)
            power = device.get_property_by(2, 1)  # 电源状态
            brightness = device.get_property_by(2, 2)  # 亮度 (1-100)
            color_temp = device.get_property_by(2, 3)  # 色温 (1700-6500K)
            color_mode = device.get_property_by(2, 4)  # 颜色模式
            color = device.get_property_by(2, 5)  # RGB颜色值
            
            status = {
                "power": power[0] if isinstance(power, list) else power,
                "brightness": brightness[0] if isinstance(brightness, list) else brightness,
                "color_temp": color_temp[0] if isinstance(color_temp, list) else color_temp,
                "color_mode": color_mode[0] if isinstance(color_mode, list) else color_mode,
                "color": color[0] if isinstance(color, list) else color,
                "online": True,
                "model": LAMP_MODEL
            }
            return json.dumps(status, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取床头灯状态失败: {e}")
        error_status = {
            "error": f"获取设备状态失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=LAMP_IP),
            "online": False,
            "model": LAMP_MODEL
        }
        return json.dumps(error_status, indent=2, ensure_ascii=False)


class PowerArgs(BaseModel):
    power: bool = Field(..., description="床头灯电源状态，true 开启，false 关闭")


@tool("set_lamp_power", args_schema=PowerArgs, description="开启或关闭床头灯。power=true 开启，power=false 关闭")
def set_lamp_power(power: bool):
    """开启或关闭床头灯"""
    try:
        with device_lock:  # 使用锁确保串行执行
            if power:
                result = device.on()
            else:
                result = device.off()
            action = "开启" if power else "关闭"
            logger.info(f"床头灯已{action}")
            return json.dumps({
                "message": f"床头灯已{action}",
                "power": power,
                "result": str(result)
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置床头灯电源失败: {e}")
        return json.dumps({
            "error": f"设置电源状态失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=LAMP_IP),
            "online": False,
            "model": LAMP_MODEL
        }, indent=2, ensure_ascii=False)


class BrightnessArgs(BaseModel):
    brightness: int = Field(..., ge=1, le=100, description="亮度值，范围 1-100")


@tool("set_lamp_brightness", args_schema=BrightnessArgs, description="设置床头灯亮度（1-100）")
def set_lamp_brightness(brightness: int):
    """设置床头灯亮度"""
    try:
        with device_lock:
            # 参考 Iot.py - 设置亮度 (siid=2, piid=2)
            result = device.set_property_by(2, 2, brightness)
            logger.info(f"亮度已设置为{brightness}%")
            return json.dumps({
                "message": f"亮度已设置为{brightness}%",
                "brightness": brightness,
                "result": str(result)
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置床头灯亮度失败: {e}")
        return json.dumps({
            "error": f"设置亮度失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=LAMP_IP),
            "online": False,
            "model": LAMP_MODEL
        }, indent=2, ensure_ascii=False)


class ColorTempArgs(BaseModel):
    color_temp: int = Field(..., ge=1700, le=6500, description="色温值，范围 1700-6500K")


@tool("set_lamp_color_temp", args_schema=ColorTempArgs, description="设置床头灯色温（1700-6500K，暖光到冷光）")
def set_lamp_color_temp(color_temp: int):
    """设置床头灯色温"""
    try:
        with device_lock:
            # 参考 Iot.py - 设置色温 (siid=2, piid=3)
            result = device.set_property_by(2, 3, color_temp)
            temp_desc = "暖光" if color_temp < 3000 else "中性光" if color_temp < 5000 else "冷光"
            logger.info(f"色温已设置为{color_temp}K ({temp_desc})")
            return json.dumps({
                "message": f"色温已设置为{color_temp}K ({temp_desc})",
                "color_temp": color_temp,
                "description": temp_desc,
                "result": str(result)
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置床头灯色温失败: {e}")
        return json.dumps({
            "error": f"设置色温失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=LAMP_IP),
            "online": False,
            "model": LAMP_MODEL
        }, indent=2, ensure_ascii=False)


class ColorArgs(BaseModel):
    red: int = Field(..., ge=0, le=255, description="红色值，范围 0-255")
    green: int = Field(..., ge=0, le=255, description="绿色值，范围 0-255")
    blue: int = Field(..., ge=0, le=255, description="蓝色值，范围 0-255")


@tool("set_lamp_color", args_schema=ColorArgs, description="设置床头灯RGB颜色（红、绿、蓝各0-255）")
def set_lamp_color(red: int, green: int, blue: int):
    """设置床头灯RGB颜色"""
    try:
        with device_lock:
            # 参考 Iot.py - 设置RGB颜色 (siid=2, piid=5)
            color_value = (red << 16) | (green << 8) | blue
            result = device.set_property_by(2, 5, color_value)
            logger.info(f"颜色已设置为 RGB({red}, {green}, {blue})")
            return json.dumps({
                "message": f"颜色已设置为 RGB({red}, {green}, {blue})",
                "red": red,
                "green": green,
                "blue": blue,
                "color_hex": f"#{red:02x}{green:02x}{blue:02x}",
                "result": str(result)
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置床头灯颜色失败: {e}")
        return json.dumps({
            "error": f"设置颜色失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=LAMP_IP),
            "online": False,
            "model": LAMP_MODEL
        }, indent=2, ensure_ascii=False)


class SceneArgs(BaseModel):
    scene: str = Field(..., description="场景名称: 'reading' (阅读), 'sleep' (睡眠), 'romantic' (浪漫), 'night' (夜灯)")


@tool("set_lamp_scene", args_schema=SceneArgs, description="设置床头灯预设场景（阅读/睡眠/浪漫/夜灯）")
def set_lamp_scene(scene: str):
    """设置床头灯预设场景"""
    # 定义预设场景
    scenes = {
        "reading": {"brightness": 100, "color_temp": 4000, "desc": "阅读模式：100%亮度，4000K中性光"},
        "sleep": {"brightness": 10, "color_temp": 2000, "desc": "睡眠模式：10%亮度，2000K暖光"},
        "romantic": {"brightness": 30, "color": (255, 100, 100), "desc": "浪漫模式：30%亮度，粉红色"},
        "night": {"brightness": 5, "color_temp": 1700, "desc": "夜灯模式：5%亮度，1700K极暖光"}
    }
    
    if scene not in scenes:
        return json.dumps({
            "error": f"未知场景: {scene}",
            "available_scenes": list(scenes.keys())
        }, indent=2, ensure_ascii=False)
    
    try:
        with device_lock:
            scene_config = scenes[scene]
            
            # 设置亮度
            device.set_property_by(2, 2, scene_config["brightness"])
            time.sleep(0.3)  # 给设备一点响应时间
            
            # 设置色温或颜色
            if "color_temp" in scene_config:
                device.set_property_by(2, 3, scene_config["color_temp"])
            elif "color" in scene_config:
                r, g, b = scene_config["color"]
                color_value = (r << 16) | (g << 8) | b
                device.set_property_by(2, 5, color_value)
            
            logger.info(f"场景已设置为: {scene}")
            return json.dumps({
                "message": f"场景已设置为: {scene}",
                "scene": scene,
                "description": scene_config["desc"],
                "config": scene_config
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置床头灯场景失败: {e}")
        return json.dumps({
            "error": f"设置场景失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=LAMP_IP),
            "online": False,
            "model": LAMP_MODEL
        }, indent=2, ensure_ascii=False)

