from miio import DeviceFactory, Device
from miio.miot_device import MiotDevice

print("=" * 60)
print("测试连接床头灯 (Yeelink Bedside Lamp)")
print("=" * 60)

# 床头灯配置
LAMP_IP = "192.168.110.128"
LAMP_TOKEN = "4a90f98aaa1273ca34685d66d6e13958"
LAMP_MODEL = "yeelink.light.bslamp2"

# 方法1: 使用 DeviceFactory 自动检测设备类型
print("\n[方法1] 使用 DeviceFactory 自动检测设备类型...")
try:
    device = DeviceFactory.create(LAMP_IP, LAMP_TOKEN)
    print(f"✓ 设备信息: {device.info()}")
    print(f"✓ 设备型号: {device.model}")
    
    # 开启设备
    result = device.off()
    print(f"✓ 开启结果: {result}")
    
    # 获取状态
    status = device.status()
    print(f"✓ 设备状态: {status}")
    
except Exception as e:
    print(f"✗ 方法1失败: {e}")
    print("\n[方法2] 使用 MIoT 协议直接控制...")
    
    try:
        # 方法2: 直接使用 MIoT 设备类
        device = MiotDevice(
            ip=LAMP_IP, 
            token=LAMP_TOKEN,
            model=LAMP_MODEL
        )
        
        print(f"✓ 设备信息: {device.info()}")
        
        # 使用 MIoT 协议获取和控制床头灯
        # siid=2 (灯光服务), piid=1-5 (各种属性)
        # 参考: https://home.miot-spec.com/spec?type=urn:miot-spec-v2:device:light:0000A001:yeelink-bslamp2:1
        
        print("\n--- 获取当前状态 ---")
        power = device.get_property_by(2, 1)  # 电源状态
        brightness = device.get_property_by(2, 2)  # 亮度 (1-100)
        color_temp = device.get_property_by(2, 3)  # 色温 (1700-6500K)
        color_mode = device.get_property_by(2, 4)  # 颜色模式
        color = device.get_property_by(2, 5)  # RGB颜色值
        
        print(f"电源状态: {'开启' if power else '关闭'} ({power})")
        print(f"亮度: {brightness}%")
        print(f"色温: {color_temp}K")
        print(f"颜色模式: {color_mode} (1=色温, 2=RGB, 3=HSV)")
        print(f"RGB颜色值: {color} (0x{color:06x})")
        
        print("\n--- 测试控制命令 ---")
        
        # 1. 开启床头灯
        print("\n1. 开启床头灯...")
        result = device.set_property_by(2, 1, True)
        print(f"   结果: {result}")
        
        # 2. 设置亮度为50%
        print("\n2. 设置亮度为50%...")
        result = device.set_property_by(2, 2, 50)
        print(f"   结果: {result}")
        
        # 3. 设置色温为3000K (暖光)
        print("\n3. 设置色温为3000K (暖光)...")
        result = device.set_property_by(2, 3, 3000)
        print(f"   结果: {result}")
        
        # 4. 设置颜色为红色 (RGB: 255, 0, 0)
        print("\n4. 设置颜色为红色...")
        red_color = (255 << 16) | (0 << 8) | 0  # 0xFF0000
        result = device.set_property_by(2, 5, red_color)
        print(f"   结果: {result}")
        
        # 5. 最后获取状态确认
        print("\n--- 最终状态 ---")
        power = device.get_property_by(2, 1)
        brightness = device.get_property_by(2, 2)
        color_temp = device.get_property_by(2, 3)
        
        print(f"电源: {'开启' if power else '关闭'}")
        print(f"亮度: {brightness}%")
        print(f"色温: {color_temp}K")
        
        print("\n✓ 床头灯连接和控制测试成功!")
        
    except Exception as e2:
        print(f"✗ 方法2也失败: {e2}")
        import traceback
        traceback.print_exc()

