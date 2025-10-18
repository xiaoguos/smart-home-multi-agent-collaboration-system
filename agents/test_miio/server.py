from fastmcp import FastMCP
from miio import AirConditioningCompanionMcn02

mcp = FastMCP("Home MCP")


class AirConditioner:
    """空调控制器类"""

    # 类变量 - 所有方法共享
    DEVICE_IP = "192.200.1.12"
    DEVICE_TOKEN = "1724bf8d57b355173dfa08ae23367f86"
    _device = None  # 设备实例

    @classmethod
    def initialize(cls):
        """初始化设备连接"""
        try:
            cls._device = AirConditioningCompanionMcn02(cls.DEVICE_IP, cls.DEVICE_TOKEN)
            print(f"✅ 设备初始化成功: {cls.DEVICE_IP}")
            return True
        except Exception as e:
            print(f"❌ 设备初始化失败: {e}")
            return False


# 初始化设备
AirConditioner.initialize()


# 使用静态方法定义工具
@mcp.tool(
    name="set_on",
    description="Turn on the air conditioner",
)
def set_on() -> str:
    """开启空调"""
    if AirConditioner._device is None:
        return "❌ 设备未初始化"

    try:
        AirConditioner._device.on()
        return "✅ 空调已开启"
    except Exception as e:
        return f"❌ 开启失败: {e}"


@mcp.tool(
    name="set_off",
    description="Turn off the air conditioner",
)
def set_off() -> str:
    """关闭空调"""
    if AirConditioner._device is None:
        return "❌ 设备未初始化"

    try:
        AirConditioner._device.off()
        return "✅ 空调已关闭"
    except Exception as e:
        return f"❌ 关闭失败: {e}"


@mcp.tool(
    name="get_status",
    description="Get air conditioner status",
)
def get_status() -> dict:
    """获取空调状态"""
    if AirConditioner._device is None:
        return {"error": "设备未初始化"}

    try:
        status = AirConditioner._device.status()
        return {
            "success": True,
            "status": str(status),
            "device_ip": AirConditioner.DEVICE_IP
        }
    except Exception as e:
        return {"error": f"获取状态失败: {e}"}


@mcp.tool(
    name="set_temperature",
    description="Set air conditioner temperature",
)
def set_temperature(temp: int) -> str:
    """设置温度"""
    if AirConditioner._device is None:
        return "❌ 设备未初始化"

    try:
        # 尝试不同的温度设置方法
        # 需要根据实际的红外指令映射来调整
        result = AirConditioner._device.send_command(temp + 10)  # 示例映射
        return f"✅ 温度设置为 {temp}°C - 结果: {result}"
    except Exception as e:
        return f"❌ 温度设置失败: {e}"


@mcp.tool(
    name="get_device_info",
    description="Get device information",
)
def get_device_info() -> dict:
    """获取设备信息"""
    if AirConditioner._device is None:
        return {"error": "设备未初始化"}

    try:
        info = AirConditioner._device.info()
        return {
            "device_ip": AirConditioner.DEVICE_IP,
            "model": info.model,
            "firmware": info.firmware_version,
            "mac_address": info.mac_address
        }
    except Exception as e:
        return {"error": f"获取信息失败: {e}"}


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)