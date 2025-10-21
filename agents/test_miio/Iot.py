from miio import DeviceFactory, Device

# 方法1: 使用 DeviceFactory 自动检测设备类型
try:
    device = DeviceFactory.create("192.168.110.129", "569905df67a11d6b67a575097255c798")
    print(f"设备信息: {device.info()}")
    print(f"设备型号: {device.model}")
    
    # 开启设备
    result = device.on()
    print(f"开启结果: {result}")
    
    # 获取状态
    status = device.status()
    print(f"设备状态: {status}")
    
except Exception as e:
    print(f"方法1失败: {e}")
    print("\n尝试方法2: 使用 MIoT 协议")
    
    # 方法2: 直接使用 MIoT 设备类
    from miio.miot_device import MiotDevice
    
    # zhimi-oa1 的 MIoT 设备
    device = MiotDevice(
        ip="192.168.110.129", 
        token="569905df67a11d6b67a575097255c798",
        model="zhimi.airp.oa1"  # 或者 zhimi.airpurifier.oa1
    )
    
    print(f"设备信息: {device.info()}")
    
    # 使用 MIoT 协议发送命令
    # siid=2 (空气净化器服务), piid=1 (电源属性)
    # 参考文档: https://home.miot-spec.com/spec?type=urn:miot-spec-v2:device:air-purifier:0000A007:zhimi-oa1:1
    
    # 开启设备 (设置电源为 true)
    result = device.set_property_by(2, 1, True)
    print(f"开启结果: {result}")
    
    # 获取电源状态
    power_status = device.get_property_by(2, 1)
    print(f"电源状态: {power_status}")

