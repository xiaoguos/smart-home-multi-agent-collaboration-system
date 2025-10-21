"""调试床头灯命令"""
from miio.miot_device import MiotDevice
import json

# 床头灯配置
LAMP_IP = "192.168.110.128"
LAMP_TOKEN = "4a90f98aaa1273ca34685d66d6e13958"
LAMP_MODEL = "yeelink.light.bslamp2"

print("=" * 60)
print("调试床头灯命令")
print("=" * 60)

# 创建设备
device = MiotDevice(
    ip=LAMP_IP,
    token=LAMP_TOKEN,
    model=LAMP_MODEL
)

print("\n测试1: 获取设备信息")
try:
    info = device.info()
    print(f"设备信息: {info}")
except Exception as e:
    print(f"错误: {e}")

print("\n测试2: 获取电源状态")
try:
    power = device.get_property_by(2, 1)
    print(f"返回值类型: {type(power)}")
    print(f"返回值: {power}")
    print(f"返回值内容: {repr(power)}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

print("\n测试3: 设置电源为开启")
try:
    result = device.set_property_by(2, 1, True)
    print(f"返回值类型: {type(result)}")
    print(f"返回值: {result}")
    print(f"返回值内容: {repr(result)}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

print("\n测试4: 再次获取电源状态")
try:
    power = device.get_property_by(2, 1)
    print(f"电源状态: {power}")
except Exception as e:
    print(f"错误: {e}")

print("\n" + "=" * 60)

