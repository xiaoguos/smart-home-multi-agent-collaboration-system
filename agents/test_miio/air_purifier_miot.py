"""
桌面空气净化器控制示例 (zhimi-oa1)
使用 MIoT 协议控制小米桌面空气净化器

设备规格参考: https://home.miot-spec.com/spec?type=urn:miot-spec-v2:device:air-purifier:0000A007:zhimi-oa1:1

主要服务和属性:
- siid=2: 空气净化器服务
  - piid=1: 电源开关 (bool)
  - piid=2: 风扇等级 (1-3)
  - piid=3: 工作模式 (0=Auto, 1=Sleep, 2=Favorite)
- siid=3: 环境监测
  - piid=1: 相对湿度 (0-100)
  - piid=6: PM2.5 密度 (0-600)
- siid=4: 滤芯
  - piid=1: 滤芯剩余寿命 (0-100)
  - piid=3: 滤芯剩余使用时间 (小时)
- siid=5: 警报
  - piid=1: 物理控制锁定 (bool)
- siid=6: 指示灯
  - piid=1: LED 亮度 (0=关, 1=暗, 2=亮)
- siid=7: 蜂鸣器
  - piid=1: 蜂鸣器开关 (bool)
"""

from miio.miot_device import MiotDevice
import json


class AirPurifierOA1:
    """桌面空气净化器 (zhimi-oa1) 控制类"""
    
    def __init__(self, ip: str, token: str):
        self.device = MiotDevice(
            ip=ip,
            token=token,
            model="zhimi.airp.oa1"
        )
        
    def get_info(self):
        """获取设备信息"""
        return self.device.info()
    
    # ========== 电源控制 ==========
    def power_on(self):
        """开启设备"""
        return self.device.set_property_by(2, 1, True)
    
    def power_off(self):
        """关闭设备"""
        return self.device.set_property_by(2, 1, False)
    
    def get_power_status(self):
        """获取电源状态"""
        return self.device.get_property_by(2, 1)
    
    # ========== 风扇控制 ==========
    def set_fan_level(self, level: int):
        """
        设置风扇等级
        :param level: 1-3 (1=低速, 2=中速, 3=高速)
        """
        if level not in [1, 2, 3]:
            raise ValueError("风扇等级必须是 1、2 或 3")
        return self.device.set_property_by(2, 2, level)
    
    def get_fan_level(self):
        """获取当前风扇等级"""
        return self.device.get_property_by(2, 2)
    
    # ========== 工作模式 ==========
    def set_mode(self, mode: int):
        """
        设置工作模式
        :param mode: 0=自动, 1=睡眠, 2=喜爱
        """
        if mode not in [0, 1, 2]:
            raise ValueError("模式必须是 0(自动)、1(睡眠) 或 2(喜爱)")
        return self.device.set_property_by(2, 3, mode)
    
    def get_mode(self):
        """获取当前工作模式"""
        return self.device.get_property_by(2, 3)
    
    # ========== 环境监测 ==========
    def get_humidity(self):
        """获取相对湿度 (0-100)"""
        return self.device.get_property_by(3, 1)
    
    def get_pm25(self):
        """获取 PM2.5 密度 (0-600 μg/m³)"""
        return self.device.get_property_by(3, 6)
    
    # ========== 滤芯信息 ==========
    def get_filter_life_level(self):
        """获取滤芯剩余寿命百分比 (0-100)"""
        return self.device.get_property_by(4, 1)
    
    def get_filter_left_time(self):
        """获取滤芯剩余使用时间 (小时)"""
        return self.device.get_property_by(4, 3)
    
    # ========== 其他设置 ==========
    def set_child_lock(self, locked: bool):
        """设置童锁"""
        return self.device.set_property_by(5, 1, locked)
    
    def get_child_lock(self):
        """获取童锁状态"""
        return self.device.get_property_by(5, 1)
    
    def set_led_brightness(self, brightness: int):
        """
        设置 LED 亮度
        :param brightness: 0=关, 1=暗, 2=亮
        """
        if brightness not in [0, 1, 2]:
            raise ValueError("亮度必须是 0(关)、1(暗) 或 2(亮)")
        return self.device.set_property_by(6, 1, brightness)
    
    def get_led_brightness(self):
        """获取 LED 亮度"""
        return self.device.get_property_by(6, 1)
    
    def set_buzzer(self, enabled: bool):
        """设置蜂鸣器开关"""
        return self.device.set_property_by(7, 1, enabled)
    
    def get_buzzer(self):
        """获取蜂鸣器状态"""
        return self.device.get_property_by(7, 1)
    
    # ========== 综合状态 ==========
    def get_status(self):
        """获取设备完整状态"""
        try:
            status = {
                "power": self.get_power_status(),
                "fan_level": self.get_fan_level(),
                "mode": self.get_mode(),
                "humidity": self.get_humidity(),
                "pm25": self.get_pm25(),
                "filter_life_level": self.get_filter_life_level(),
                "filter_left_time": self.get_filter_left_time(),
                "child_lock": self.get_child_lock(),
                "led_brightness": self.get_led_brightness(),
                "buzzer": self.get_buzzer()
            }
            return status
        except Exception as e:
            return {"error": str(e)}


def main():
    """主函数 - 测试示例"""
    
    # 创建设备实例
    purifier = AirPurifierOA1(
        ip="192.168.110.129",
        token="569905df67a11d6b67a575097255c798"
    )
    
    print("=" * 50)
    print("桌面空气净化器控制测试")
    print("=" * 50)
    
    # # 1. 获取设备信息
    # print("\n1. 设备信息:")
    # try:
    #     info = purifier.get_info()
    #     print(f"   型号: {info.model}")
    #     print(f"   固件版本: {info.firmware_version}")
    #     print(f"   硬件版本: {info.hardware_version}")
    # except Exception as e:
    #     print(f"   错误: {e}")
    #
    # # 2. 获取完整状态
    # print("\n2. 设备状态:")
    # status = purifier.get_status()
    # print(json.dumps(status, indent=2, ensure_ascii=False))
    #
    # # 3. 开启设备
    # print("\n3. 开启设备:")
    # try:
    #     result = purifier.power_on()
    #     print(f"   结果: {result}")
    # except Exception as e:
    #     print(f"   错误: {e}")
    #
    # # 4. 设置为自动模式
    # print("\n4. 设置为自动模式:")
    # try:
    #     result = purifier.set_mode(0)  # 0=自动
    #     print(f"   结果: {result}")
    # except Exception as e:
    #     print(f"   错误: {e}")
    
    # 5. 设置风扇等级
    print("\n5. 设置风扇等级为中速:")
    try:
        result = purifier.set_fan_level(1)  # 2=中速
        print(f"   结果: {result}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 6. 设置 LED 亮度
    print("\n6. 设置 LED 为暗:")
    try:
        result = purifier.set_led_brightness(1)  # 1=暗
        print(f"   结果: {result}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 7. 获取环境数据
    print("\n7. 环境监测数据:")
    try:
        print(f"   PM2.5: {purifier.get_pm25()} μg/m³")
        print(f"   湿度: {purifier.get_humidity()}%")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 8. 获取滤芯信息
    print("\n8. 滤芯信息:")
    try:
        print(f"   剩余寿命: {purifier.get_filter_life_level()}%")
        print(f"   剩余时间: {purifier.get_filter_left_time()} 小时")
    except Exception as e:
        print(f"   错误: {e}")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()

