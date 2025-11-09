from miio import DeviceFactory
from miio.miot_device import MiotDevice
import json

# 设备配置
PURIFIER_IP = "192.168.110.120"
PURIFIER_TOKEN = "569905df67a11d6b67a575097255c798"
PURIFIER_MODEL = "zhimi.airp.oa1"

# 创建设备实例
miot_device = MiotDevice(ip=PURIFIER_IP, token=PURIFIER_TOKEN, model=PURIFIER_MODEL)

# 关闭电源
miot_device.set_property_by(2, 1, True)
# 设置风机档位
miot_device.set_property_by(2, 5, 4)
#设置按键亮度
miot_device.set_property_by(2, 6, False)
# 设置提示音
miot_device.set_property_by(2, 7, True)
# 物理控制锁(儿童锁)
miot_device.set_property_by(2, 9, False)
print(miot_device.get_property_by(4, 1))