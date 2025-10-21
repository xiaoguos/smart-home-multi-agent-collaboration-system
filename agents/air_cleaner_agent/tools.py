from langchain_core.tools import tool
from miio.miot_device import MiotDevice
import json
from pydantic import BaseModel, Field

# 初始化桌面空气净化器设备 (zhimi-oa1)
# 使用 MIoT 协议
device = MiotDevice(
    ip="192.168.110.129",
    token="569905df67a11d6b67a575097255c798",
    model="zhimi.airp.oa1"
)


@tool("get_purifier_status", description="获取空气净化器当前状态，包括电源、PM2.5、湿度、风扇等级、工作模式、滤芯寿命等信息")
def get_purifier_status():
    """获取空气净化器设备状态并以 JSON 格式返回"""
    try:
        status = {
            "power": device.get_property_by(2, 1),  # 电源状态
            "fan_level": device.get_property_by(2, 2),  # 风扇等级 (1-3)
            "mode": device.get_property_by(2, 3),  # 工作模式 (0=自动, 1=睡眠, 2=喜爱)
            "humidity": device.get_property_by(3, 1),  # 湿度
            "pm25": device.get_property_by(3, 6),  # PM2.5
            "filter_life_level": device.get_property_by(4, 1),  # 滤芯剩余寿命 (%)
            "filter_left_time": device.get_property_by(4, 3),  # 滤芯剩余时间 (小时)
            "child_lock": device.get_property_by(5, 1),  # 童锁
            "led_brightness": device.get_property_by(6, 1),  # LED亮度 (0=关, 1=暗, 2=亮)
            "buzzer": device.get_property_by(7, 1),  # 蜂鸣器
            "online": True,
            "model": "zhimi.airp.oa1"
        }
        return json.dumps(status, indent=2, ensure_ascii=False)
    except Exception as e:
        error_status = {
            "error": str(e),
            "online": False,
            "model": "zhimi.airp.oa1"
        }
        return json.dumps(error_status, indent=2, ensure_ascii=False)


class PowerArgs(BaseModel):
    power: bool = Field(..., description="空气净化器电源状态，true 开启，false 关闭")


@tool("set_purifier_power", args_schema=PowerArgs, description="开启或关闭空气净化器。power=true 开启，power=false 关闭")
def set_purifier_power(power: bool):
    """开启或关闭空气净化器"""
    try:
        result = device.set_property_by(2, 1, power)
        action = "开启" if power else "关闭"
        return json.dumps({
            "message": f"空气净化器已{action}",
            "power": power,
            "result": result
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "online": False,
            "model": "zhimi.airp.oa1"
        }, indent=2, ensure_ascii=False)


class FanLevelArgs(BaseModel):
    level: int = Field(..., ge=1, le=3, description="风扇等级，范围 1-3 (1=低速, 2=中速, 3=高速)")


@tool("set_purifier_fan_level", args_schema=FanLevelArgs, description="设置空气净化器风扇等级（1=低速，2=中速，3=高速）")
def set_purifier_fan_level(level: int):
    """设置空气净化器风扇等级"""
    try:
        result = device.set_property_by(2, 2, level)
        level_name = {1: "低速", 2: "中速", 3: "高速"}[level]
        return json.dumps({
            "message": f"风扇等级已设置为{level_name}",
            "fan_level": level,
            "result": result
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "online": False,
            "model": "zhimi.airp.oa1"
        }, indent=2, ensure_ascii=False)


class ModeArgs(BaseModel):
    mode: int = Field(..., ge=0, le=2, description="工作模式，0=自动模式，1=睡眠模式，2=喜爱模式")


@tool("set_purifier_mode", args_schema=ModeArgs, description="设置空气净化器工作模式（0=自动，1=睡眠，2=喜爱）")
def set_purifier_mode(mode: int):
    """设置空气净化器工作模式"""
    try:
        result = device.set_property_by(2, 3, mode)
        mode_name = {0: "自动模式", 1: "睡眠模式", 2: "喜爱模式"}[mode]
        return json.dumps({
            "message": f"工作模式已设置为{mode_name}",
            "mode": mode,
            "result": result
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "online": False,
            "model": "zhimi.airp.oa1"
        }, indent=2, ensure_ascii=False)


class LEDBrightnessArgs(BaseModel):
    brightness: int = Field(..., ge=0, le=2, description="LED亮度，0=关闭，1=暗，2=亮")


@tool("set_purifier_led", args_schema=LEDBrightnessArgs, description="设置空气净化器LED指示灯亮度（0=关闭，1=暗，2=亮）")
def set_purifier_led(brightness: int):
    """设置空气净化器LED亮度"""
    try:
        result = device.set_property_by(6, 1, brightness)
        brightness_name = {0: "关闭", 1: "暗", 2: "亮"}[brightness]
        return json.dumps({
            "message": f"LED已设置为{brightness_name}",
            "led_brightness": brightness,
            "result": result
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "online": False,
            "model": "zhimi.airp.oa1"
        }, indent=2, ensure_ascii=False)