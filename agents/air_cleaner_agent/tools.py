from langchain_core.tools import tool
from miio import DeviceFactory
from miio.miot_device import MiotDevice
import json
from pydantic import BaseModel, Field
import logging
import threading

# 配置日志
logger = logging.getLogger(__name__)

# 设备配置
PURIFIER_IP = "192.168.110.120"
PURIFIER_TOKEN = "569905df67a11d6b67a575097255c798"
PURIFIER_MODEL = "zhimi.airp.oa1"

# 创建设备实例（使用 DeviceFactory 自动识别设备类型）
device = DeviceFactory.create(PURIFIER_IP, PURIFIER_TOKEN)

# 同时保留 MiotDevice 实例用于属性设置
miot_device = MiotDevice(
    ip=PURIFIER_IP,
    token=PURIFIER_TOKEN,
    model=PURIFIER_MODEL
)

# 添加线程锁，确保同一时间只有一个操作
device_lock = threading.Lock()


@tool("get_purifier_status", description="获取空气净化器当前状态，包括电源、PM2.5、湿度、风扇等级、工作模式、滤芯寿命等信息")
def get_purifier_status():
    """获取空气净化器设备状态并以 JSON 格式返回"""
    try:
        with device_lock:  # 使用锁确保串行执行
            # 使用 status() 方法一次性获取所有状态
            status_obj = device.status()
            
            # 获取状态数据字典
            if hasattr(status_obj, 'data'):
                status_data = status_obj.data
                # 添加额外信息
                status_data['online'] = True
                status_data['model'] = PURIFIER_MODEL
                return json.dumps(status_data, indent=2, ensure_ascii=False, default=str)
            else:
                # 降级方案：如果没有 data 属性，手动获取关键属性
                logger.warning("设备状态对象没有 data 属性，使用降级方案")
                power = miot_device.get_property_by(2, 1)
                fan_level = miot_device.get_property_by(2, 5)  # 正确的 PIID
                led = miot_device.get_property_by(2, 6)
                
                status = {
                    "power": power[0].get('value') if isinstance(power, list) and len(power) > 0 else power,
                    "fan_level": fan_level[0].get('value') if isinstance(fan_level, list) and len(fan_level) > 0 else fan_level,
                    "led_brightness": led[0].get('value') if isinstance(led, list) and len(led) > 0 else led,
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
            result = miot_device.set_property_by(2, 1, power)
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
    level: int = Field(..., ge=1, le=4, description="风扇等级，范围 1-4 (1档、2档、3档、4档)")


@tool("set_purifier_fan_level", args_schema=FanLevelArgs, description="设置空气净化器风扇等级（1档、2档、3档、4档）")
def set_purifier_fan_level(level: int):
    """设置空气净化器风扇等级"""
    try:
        with device_lock:
            result = miot_device.set_property_by(2, 5, level)  # 正确的 PIID 是 5
            logger.info(f"风扇等级已设置为{level}档")
            return json.dumps({
                "message": f"风扇等级已设置为{level}档",
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


class LEDBrightnessArgs(BaseModel):
    brightness: bool = Field(..., description="LED按键亮度开关，true 开启，false 关闭")


@tool("set_purifier_led", args_schema=LEDBrightnessArgs, description="设置空气净化器LED按键亮度开关")
def set_purifier_led(brightness: bool):
    """设置空气净化器LED按键亮度"""
    try:
        with device_lock:
            result = miot_device.set_property_by(2, 6, brightness)  # 正确的 PIID 是 (2, 6)
            status = "开启" if brightness else "关闭"
            logger.info(f"LED亮度已{status}")
            return json.dumps({
                "message": f"LED亮度已{status}",
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


class AlarmArgs(BaseModel):
    alarm: bool = Field(..., description="提示音开关，true 开启，false 关闭")


@tool("set_purifier_alarm", args_schema=AlarmArgs, description="设置空气净化器提示音开关")
def set_purifier_alarm(alarm: bool):
    """设置空气净化器提示音"""
    try:
        with device_lock:
            result = miot_device.set_property_by(2, 7, alarm)  # PIID 7: alarm
            status = "开启" if alarm else "关闭"
            logger.info(f"提示音已{status}")
            return json.dumps({
                "message": f"提示音已{status}",
                "alarm": alarm,
                "result": str(result)
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器提示音失败: {e}")
        return json.dumps({
            "error": f"设置提示音失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=PURIFIER_IP),
            "online": False,
            "model": PURIFIER_MODEL
        }, indent=2, ensure_ascii=False)


class ChildLockArgs(BaseModel):
    child_lock: bool = Field(..., description="童锁开关，true 开启，false 关闭")


@tool("set_purifier_child_lock", args_schema=ChildLockArgs, description="设置空气净化器童锁（物理控制锁）")
def set_purifier_child_lock(child_lock: bool):
    """设置空气净化器童锁"""
    try:
        with device_lock:
            result = miot_device.set_property_by(2, 9, child_lock)  # PIID 9: physical-controls-locked
            status = "开启" if child_lock else "关闭"
            logger.info(f"童锁已{status}")
            return json.dumps({
                "message": f"童锁已{status}",
                "child_lock": child_lock,
                "result": str(result)
            }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空气净化器童锁失败: {e}")
        return json.dumps({
            "error": f"设置童锁失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=PURIFIER_IP),
            "online": False,
            "model": PURIFIER_MODEL
        }, indent=2, ensure_ascii=False)