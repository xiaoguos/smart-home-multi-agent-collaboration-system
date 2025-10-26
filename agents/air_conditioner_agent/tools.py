from langchain_core.tools import tool
from miio import AirConditioningCompanionMcn02
import json
from pydantic import BaseModel, Field
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 设备配置
AC_IP = "192.168.110.131"
AC_TOKEN = "1724bf8d57b355173dfa08ae23367f86"
AC_MODEL = "lumi.acpartner.mcn02"

device = AirConditioningCompanionMcn02(ip=AC_IP, token=AC_TOKEN)


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
            "model": AC_MODEL
        }
        return json.dumps(status, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"获取空调状态失败: {e}")
        error_status = {
            "error": f"获取设备状态失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=AC_IP),
            "online": False,
            "model": AC_MODEL
        }
        return json.dumps(error_status, indent=2, ensure_ascii=False)


class PowerArgs(BaseModel):
    power: bool = Field(..., description="空调电源状态，true 开启，false 关闭")


@tool("set_ac_power", args_schema=PowerArgs, description="开启或关闭空调。power=true 开启，power=false 关闭")
def set_ac_power(power: bool):
    try:
        if power:
            device.on()
            logger.info("空调已开启")
            return json.dumps({"message": "空调已开启", "power": True}, indent=2, ensure_ascii=False)
        else:
            device.off()
            logger.info("空调已关闭")
            return json.dumps({"message": "空调已关闭", "power": False}, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空调电源失败: {e}")
        error_status = {
            "error": f"设置电源状态失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=AC_IP),
            "online": False,
            "model": AC_MODEL
        }
        return json.dumps(error_status, indent=2, ensure_ascii=False)


class TemperatureArgs(BaseModel):
    temperature: int = Field(..., ge=16, le=30, description="目标温度（摄氏度），范围 16-30")


@tool("set_ac_temperature", args_schema=TemperatureArgs, description="设置空调目标温度（16-30℃）")
def set_ac_temperature(temperature: int):
    """设置空调目标温度"""
    try:
        # 对于 mcn02，目标温度字段为 tar_temp，对应的设置命令通常为 set_tar_temp
        result = device.send("set_tar_temp", [temperature])
        logger.info(f"空调温度已设置为{temperature}℃")
        return json.dumps({
            "message": f"空调温度已设置为{temperature}℃",
            "target_temperature": temperature,
            "result": result
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"设置空调温度失败: {e}")
        error_status = {
            "error": f"设置温度失败: {str(e)}",
            "message": "请检查：\n1. 设备是否已开启并连接到网络\n2. 设备IP地址是否配置正确（当前配置：{ip}）\n3. 设备Token是否正确".format(ip=AC_IP),
            "online": False,
            "model": AC_MODEL
        }
        return json.dumps(error_status, indent=2, ensure_ascii=False)