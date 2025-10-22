"""
小米设备信息 MCP 服务
使用 FastMCP 封装小米设备信息提取功能
"""

import json
import logging
from typing import Optional
from fastmcp import FastMCP

# 导入 divice.py 中的核心类
import sys
import os
sys.path.append(os.path.dirname(__file__))

from divice import XiaomiCloudConnector

# 配置日志（MCP 模式下减少日志输出）
if "--stdio" not in sys.argv and "mcp" not in sys.argv[0].lower():
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.ERROR)
    
logger = logging.getLogger(__name__)

# 创建 FastMCP 实例
mcp = FastMCP("Xiaomi Device Info Service")


@mcp.tool()
async def get_xiaomi_devices(
    username: str,
    password: str,
    server: str = "cn",
    skip_login: bool = False
) -> str:
    """
    获取小米智能设备信息（包含登录、获取设备列表等完整流程）
    
    参数：
        username: 小米账号（邮箱、手机号或用户ID）
        password: 密码
        server: 服务器区域，可选值：cn, de, us, ru, tw, sg, in, i2（默认：cn）
        skip_login: 是否跳过登录，直接使用默认token（默认：False）
    
    返回：
        设备列表信息，包含设备名称、ID、MAC地址、IP地址、Token、型号等
    """
    try:
        logger.info(f"开始获取小米设备信息: {username}, 服务器: {server}, 跳过登录: {skip_login}")
        
        # 1. 创建连接器
        connector = XiaomiCloudConnector(username, password)
        
        # 如果不跳过登录，则执行真正的登录
        if not skip_login:
            logged_in = connector.login()
            if not logged_in:
                return json.dumps({
                    "success": False,
                    "message": "小米账号登录失败，请检查用户名和密码",
                }, ensure_ascii=False, indent=2)
            logger.info("登录成功，开始获取设备列表")
        else:
            # 跳过登录，直接使用 divice.py 中的默认 token 和参数
            logger.info("跳过登录，使用默认参数")
        
        # 2. 获取所有家庭
        all_homes = []
        
        # 获取用户自己的家庭
        homes = connector.get_homes(server)
        if homes is not None and 'result' in homes and 'homelist' in homes['result']:
            for h in homes['result']['homelist']:
                all_homes.append({
                    'home_id': h['id'],
                    'home_owner': connector.userId,
                    'home_name': h.get('name', '未命名家庭')
                })
        
        # 获取共享家庭
        dev_cnt = connector.get_dev_cnt(server)
        if dev_cnt is not None and 'result' in dev_cnt and 'share' in dev_cnt['result']:
            share_families = dev_cnt['result']['share'].get('share_family', [])
            for h in share_families:
                all_homes.append({
                    'home_id': h['home_id'],
                    'home_owner': h['home_owner'],
                    'home_name': h.get('name', '共享家庭')
                })
        
        if len(all_homes) == 0:
            return json.dumps({
                "success": False,
                "message": f"在服务器 {server} 上未找到任何家庭",
            }, ensure_ascii=False, indent=2)
        
        # 3. 获取所有设备
        all_devices = []
        for home in all_homes:
            devices = connector.get_devices(server, home['home_id'], home['home_owner'])
            
            if devices is not None and 'result' in devices and 'device_info' in devices['result']:
                device_list = devices['result']['device_info']
                
                if device_list:
                    for device in device_list:
                        device_data = {
                            "home_name": home.get('home_name'),
                            "home_id": home['home_id'],
                            "name": device.get('name', '未命名设备'),
                            "did": device.get('did'),
                            "mac": device.get('mac'),
                            "ip": device.get('localip'),
                            "token": device.get('token'),
                            "model": device.get('model'),
                            "isOnline": device.get('isOnline', False),
                            "rssi": device.get('rssi'),
                        }
                        
                        # 如果是蓝牙设备，获取 BLE key
                        if device.get('did') and 'blt' in device['did']:
                            beaconkey = connector.get_beaconkey(server, device['did'])
                            if beaconkey and 'result' in beaconkey and 'beaconkey' in beaconkey['result']:
                                device_data['ble_key'] = beaconkey['result']['beaconkey']
                        
                        all_devices.append(device_data)
        
        logger.info(f"成功获取 {len(all_devices)} 个设备")
        
        return json.dumps({
            "success": True,
            "message": f"成功获取设备列表",
            "userId": connector.userId,
            "server": server,
            "total_homes": len(all_homes),
            "total_devices": len(all_devices),
            "devices": all_devices,
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取设备信息异常: {str(e)}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": f"获取设备信息异常: {str(e)}",
        }, ensure_ascii=False, indent=2)


# 主函数，用于启动 MCP 服务器
if __name__ == "__main__":
    # 运行 MCP 服务器
    mcp.run()

