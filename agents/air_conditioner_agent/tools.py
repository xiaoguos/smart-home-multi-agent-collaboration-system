from langchain_core.tools import tool
from miio import AirConditioningCompanionMcn02
import json
from pydantic import BaseModel, Field


device = AirConditioningCompanionMcn02(ip="192.168.110.124", token="1724bf8d57b355173dfa08ae23367f86")


@tool("get_ac_status", description="获取空调当前状态")
def get_ac_status():
    """获取设备状态并以 JSON 格式返回"""
    try:
        props = device.send("get_prop", ["power", "mode", "tar_temp", "fan_level", "ver_swing", "load_power"])
        status = {
            "power": props[0],
            "mode": props[1],
            "target_temperature": props[2],
            "fan_level": props[3],
            "vertical_swing": props[4],
            "load_power": props[5],
            "online": True,
            "model": "lumi.acpartner.mcn02"
        }
        return json.dumps(status, indent=2)
    except Exception as e:
        error_status = {
            "error": str(e),
            "online": False,
            "model": "lumi.acpartner.mcn02"
        }
        return json.dumps(error_status, indent=2)


class PowerArgs(BaseModel):
    power: bool = Field(..., description="空调电源状态，true 开启，false 关闭")


@tool("set_ac_power", args_schema=PowerArgs, description="开启或关闭空调。power=true 开启，power=false 关闭")
def set_ac_power(power: bool):
    try:
        if power:
            device.on()
            return json.dumps({"message": "成功开启"}, indent=2)
        else:
            device.off()
            return json.dumps({"message": "成功关闭"}, indent=2)
    except Exception as e:
        error_status = {
            "error": str(e),
            "online": False,
            "model": "lumi.acpartner.mcn02"
        }
        return json.dumps(error_status, indent=2)


class TemperatureArgs(BaseModel):
    temperature: int = Field(..., ge=16, le=30, description="目标温度（摄氏度），范围 16-30")


@tool("set_ac_temperature", args_schema=TemperatureArgs, description="设置空调目标温度（16-30℃）")
def set_ac_temperature(temperature: int):
    """设置空调目标温度"""
    try:
        # 对于 mcn02，目标温度字段为 tar_temp，对应的设置命令通常为 set_tar_temp
        result = device.send("set_tar_temp", [temperature])
        return json.dumps({
            "message": "目标温度已更新",
            "target_temperature": temperature,
            "result": result
        }, indent=2)
    except Exception as e:
        error_status = {
            "error": str(e),
            "online": False,
            "model": "lumi.acpartner.mcn02"
        }
        return json.dumps(error_status, indent=2)