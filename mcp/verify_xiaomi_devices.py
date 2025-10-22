"""
直接通过 MCP 客户端获取小米设备信息
使用方法：python mcp/verify_xiaomi_devices.py
"""

import asyncio
import sys
import os
import json
from getpass import getpass

sys.path.append(os.path.dirname(__file__))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    """通过 MCP 客户端获取小米设备信息"""
    
    print("\n" + "="*60)
    print("小米设备信息查询（通过 MCP）")
    print("="*60 + "\n")
    
    # MCP 服务脚本路径
    mcp_script = os.path.join(os.path.dirname(__file__), "xiaomi_device_mcp.py")
    
    # 启动 MCP 服务（设置环境变量以减少日志输出）
    env = os.environ.copy()
    env["FASTMCP_LOG_LEVEL"] = "ERROR"  # 只显示错误
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[mcp_script],
        env=env
    )
    
    print("正在启动 MCP 服务...")
    sys.stdout.flush()
    
    async with stdio_client(server_params) as (stdio, write):
        session = ClientSession(stdio, write)
        await session.initialize()
        
        # 等待 MCP 服务完全启动
        await asyncio.sleep(1)
        
        print("\n" + "="*60)
        print("✓ MCP 服务已启动")
        print("="*60 + "\n")
        sys.stdout.flush()
        
        # 测试账号（硬编码）
        username = "13716858597"
        password = "WDep@26056"
        server = "cn"
        skip_login = True  # 使用默认 token，跳过登录
        
        print(f"账号: {username}")
        print(f"服务器: {server}")
        print(f"跳过登录: {skip_login}")
        print()
        
        # 调用 MCP 工具获取设备信息
        print("="*60)
        print("正在获取小米设备信息...")
        print("="*60)
        result = await session.call_tool("get_xiaomi_devices", {
            "username": username,
            "password": password,
            "server": server,
            "skip_login": skip_login
        })
        
        if result and len(result.content) > 0:
            content = result.content[0]
            response = content.text if hasattr(content, 'text') else str(content)
            data = json.loads(response)
            
            if data.get("success"):
                print(f"\n✓ 成功获取 {data.get('total_devices', 0)} 个设备")
                print(f"✓ 用户ID: {data.get('userId', '未知')}")
                print(f"✓ 共 {data.get('total_homes', 0)} 个家庭\n")
                
                devices = data.get("devices", [])
                if devices:
                    print("-"*60)
                    for i, device in enumerate(devices, 1):
                        print(f"\n设备 {i}:")
                        print(f"  名称: {device.get('name', '未命名')}")
                        print(f"  家庭: {device.get('home_name', '未知')}")
                        print(f"  型号: {device.get('model', '未知')}")
                        print(f"  在线: {'是' if device.get('isOnline') else '否'}")
                        print(f"  IP地址: {device.get('ip', '未知')}")
                        print(f"  MAC地址: {device.get('mac', '未知')}")
                        print(f"  Token: {device.get('token', '未知')}")
                        print(f"  设备ID: {device.get('did', '未知')}")
                        if device.get('ble_key'):
                            print(f"  BLE Key: {device.get('ble_key')}")
                    print("\n" + "-"*60)
                else:
                    print("未找到任何设备")
            else:
                print(f"\n✗ 获取设备信息失败: {data.get('message')}")
        
        print("\n" + "="*60)
        print("查询完成")
        print("="*60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序已取消")
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()

