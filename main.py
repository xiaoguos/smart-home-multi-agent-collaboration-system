from miio import Device
import enum
import json
import time
from datetime import datetime
dev = Device("192.200.1.12", "1724bf8d57b355173dfa08ae23367f86")
# print(dev.info())
# print(dev.model)
# print(dev.raw_id)

from miio import AirConditioningCompanionMcn02


class FanSpeed(enum.Enum):
    Auto = "auto_fan"
    Low = "small_fan"
    Medium = "medium_fan"
    High = "large_fan"

def get_ac_status_json(device):
    """获取空调状态并返回JSON格式"""
    try:
        status = device.status()

        # 直接访问属性
        status_info = {
            "is_on": status.is_on,
            "power": status.power,
            "mode": str(status.mode),  # 转换为字符串
            "mode_value": status.mode.value if hasattr(status.mode, 'value') else str(status.mode),
            "target_temperature": status.target_temperature,
            "fan_speed": str(status.fan_speed),
            "fan_speed_value": status.fan_speed.value if hasattr(status.fan_speed, 'value') else str(status.fan_speed),
            "swing_mode": str(status.swing_mode),
            "swing_mode_value": status.swing_mode.value if hasattr(status.swing_mode, 'value') else str(
                status.swing_mode),
            "current_temperature": status.current_temperature if hasattr(status, 'current_temperature') else None,
            "load_power": status.load_power,
            "timestamp": datetime.now().isoformat()
        }

        return json.dumps(status_info, indent=2, default=str)

    except Exception as e:
        return json.dumps({"error": str(e), "timestamp": datetime.now().isoformat()}, indent=2)

# 替换为您的设备IP和Token
DEVICE_IP = "192.200.1.12"
DEVICE_TOKEN = "1724bf8d57b355173dfa08ae23367f86"

# 创建设备实例
device = AirConditioningCompanionMcn02(DEVICE_IP, DEVICE_TOKEN)

# 获取设备信息（测试连接）
# print("设备信息:", device.info())

# 获取当前状态
status = device.status()
print("设备状态:", status)
# 学习红外指令（将空调伴侣置于学习模式）
print("可用方法:")
for method_name in dir(device):
    if not method_name.startswith('_'):  # 过滤掉私有方法
        print(f"  {method_name}()")

# 学习成功后，可以保存这个红外码

# 发送红外指令控制空调
# device.on()
# status = device.status()
# print(get_ac_status_json(device))
# device.send("set_prop",  [{"did": "918383809", "siid": 2, "piid": 1, "value": False}])
# result = device.send(
#     command="set_properties",
#     parameters= [{'did': 918383809,'siid': 2, 'piid': 1, 'value':False}],
#     retry_count=5
# )

# print(device.send("set_mode", ["auto"]))
# device.send_ir_code(1)  # 发送保存在第1个按键位的红外码
print(device.status)
print(device.send("get_prop", [
    "ac_state"
]))
# print(device.supported_models,end='+++++')
# print(device.set_target_temperature(25),end='+++++')