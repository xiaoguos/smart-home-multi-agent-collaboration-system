from miio import DeviceFactory
from miio.miot_device import MiotDevice
import json

# 设备配置
LAMP_IP = "192.168.110.122"
LAMP_TOKEN = "4a90f98aaa1273ca34685d66d6e13958"
LAMP_MODEL = "yeelink.light.bslamp2"

# 使用 DeviceFactory 创建设备（Yeelight 对象）
device = DeviceFactory.create(LAMP_IP, LAMP_TOKEN)

print(f"设备信息: {device.info()}")
print(f"设备类型: {type(device)}\n")

# status() 是一个方法，需要调用才能获取 DeviceStatus 对象
status = device.status()  # 注意：加上括号调用方法
print(f"状态对象类型: {type(status)}")
print(f"状态对象表示: {status}\n")

print("=" * 50)
print("方法1: 使用 descriptors() 查看所有可用属性")
print("=" * 50)
descriptors = status.descriptors()
for name, descriptor in descriptors.items():
    try:
        value = getattr(status, name)
        print(f"{name}: {value} (类型: {descriptor.id})")
    except Exception as e:
        print(f"{name}: 获取失败 - {e}")

print("\n" + "=" * 50)
print("方法2: 直接访问属性（如果知道属性名）")
print("=" * 50)
# 尝试访问常见的 Yeelight 属性
common_attrs = ['power', 'is_on', 'brightness', 'color_temp', 
                'rgb', 'color_mode', 'name', 'model']

status_dict = {}
for attr in common_attrs:
    if hasattr(status, attr):
        try:
            value = getattr(status, attr)
            status_dict[attr] = value
            print(f"{attr}: {value}")
        except Exception as e:
            print(f"{attr}: 获取失败 - {e}")

print("\n" + "=" * 50)
print("转换为 JSON 格式")
print("=" * 50)
print(json.dumps(status_dict, indent=2, ensure_ascii=False, default=str))
