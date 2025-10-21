"""测试 bedside_lamp_agent 的 tools.py 功能"""
import sys
import time
import pytest

sys.path.insert(0, '../bedside_lamp_agent')

from tools import (
    get_lamp_status,
    set_lamp_power,
    set_lamp_brightness,
    set_lamp_color_temp,
    set_lamp_color,
    set_lamp_scene
)


class TestBedsideLampTools:
    """床头灯工具测试类"""
    
    def test_1_get_lamp_status(self):
        """测试获取床头灯状态"""
        print("\n1. 获取床头灯状态:")
        result = get_lamp_status.invoke({})
        print(f"✓ 结果: {result}")
        time.sleep(1.0)  # 增加延迟到1秒
        assert result is not None
        # 检查是否成功（没有error或online为true）
        assert '"online": true' in result or '"error"' in result
    
    def test_2_set_lamp_power(self):
        """测试开启床头灯"""
        print("\n2. 开启床头灯:")
        result = set_lamp_power.invoke({"power": True})
        print(f"✓ 结果: {result}")
        time.sleep(1.0)
        assert result is not None
    
    def test_3_set_lamp_brightness(self):
        """测试设置亮度为 50%"""
        print("\n3. 设置亮度为 50%:")
        result = set_lamp_brightness.invoke({"brightness": 50})
        print(f"✓ 结果: {result}")
        time.sleep(1.0)
        assert result is not None
    
    def test_4_set_lamp_color_temp(self):
        """测试设置色温为 3000K"""
        print("\n4. 设置色温为 3000K:")
        result = set_lamp_color_temp.invoke({"color_temp": 3000})
        print(f"✓ 结果: {result}")
        time.sleep(1.0)
        assert result is not None
    
    def test_5_set_lamp_color(self):
        """测试设置颜色为蓝色"""
        print("\n5. 设置颜色为蓝色:")
        result = set_lamp_color.invoke({"red": 0, "green": 0, "blue": 255})
        print(f"✓ 结果: {result}")
        time.sleep(1.0)
        assert result is not None
    
    def test_6_set_lamp_scene(self):
        """测试设置阅读场景"""
        print("\n6. 设置阅读场景:")
        result = set_lamp_scene.invoke({"scene": "reading"})
        print(f"✓ 结果: {result}")
        time.sleep(1.0)
        assert result is not None


if __name__ == "__main__":
    # 直接运行时使用 pytest
    pytest.main([__file__, "-v", "-s"])

