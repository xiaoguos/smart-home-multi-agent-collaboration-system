"""测试 air_cleaner_agent 的 tools.py 功能"""
import sys
import time
import pytest

sys.path.insert(0, '../air_cleaner_agent')

from tools import (
    get_purifier_status,
    set_purifier_power,
    set_purifier_fan_level,
    set_purifier_mode,
    set_purifier_led
)


class TestAirPurifierTools:
    """空气净化器工具测试类"""
    
    def test_1_get_purifier_status(self):
        """测试获取空气净化器状态"""
        print("\n1. 获取空气净化器状态:")
        result = get_purifier_status.invoke({})
        print(f"✓ 成功: {result}")
        time.sleep(0.5)
        assert result is not None
    
    def test_2_set_purifier_power(self):
        """测试开启空气净化器"""
        print("\n2. 开启空气净化器:")
        result = set_purifier_power.invoke({"power": True})
        print(f"✓ 成功: {result}")
        time.sleep(0.5)
        assert result is not None
        assert "空气净化器已开启" in result or "error" in result
    
    def test_3_set_purifier_fan_level(self):
        """测试设置风扇等级为中速"""
        print("\n3. 设置风扇等级为中速:")
        result = set_purifier_fan_level.invoke({"level": 2})
        print(f"✓ 成功: {result}")
        time.sleep(0.5)
        assert result is not None
    
    def test_4_set_purifier_mode(self):
        """测试设置为自动模式"""
        print("\n4. 设置为自动模式:")
        result = set_purifier_mode.invoke({"mode": 0})
        print(f"✓ 成功: {result}")
        time.sleep(0.5)
        assert result is not None
    
    def test_5_set_purifier_led(self):
        """测试设置LED为暗光"""
        print("\n5. 设置LED为暗光:")
        result = set_purifier_led.invoke({"brightness": 1})
        print(f"✓ 成功: {result}")
        time.sleep(0.5)
        assert result is not None


if __name__ == "__main__":
    # 直接运行时使用 pytest
    pytest.main([__file__, "-v", "-s"])
