"""
设备查询 MCP 服务
提供从数据库获取小米设备信息的功能
供用户和 Agent 查询设备列表、设备详情等
"""

import json
import logging
import sys
import os
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP
import yaml
from pathlib import Path
import pymysql
from pymysql.cursors import DictCursor

# 导入 XiaomiCloudConnector 类
backend_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'backend-python')
sys.path.insert(0, backend_path)
from api.xiaomi_auth import XiaomiCloudConnector

# 配置日志（MCP 模式下减少日志输出）
if "--stdio" not in sys.argv and "mcp" not in sys.argv[0].lower():
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.ERROR)
    
logger = logging.getLogger(__name__)

# 创建 FastMCP 实例
mcp = FastMCP("Device Query Service", version="1.0.0")


def load_config(config_path: str = "../config.yaml") -> dict:
    """加载配置文件"""
    try:
        if not os.path.isabs(config_path):
            current_dir = Path(__file__).parent
            yaml_path = (current_dir / config_path).resolve()
        else:
            yaml_path = Path(config_path)
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}


def get_database_connection():
    """获取数据库连接"""
    try:
        config = load_config()
        db_type = config.get('database', {}).get('type', 'starrocks')
        db_config = config.get('database', {}).get(db_type, {})
        
        connection = pymysql.connect(
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 9030),
            user=db_config.get('user', 'root'),
            password=db_config.get('password', ''),
            database=db_config.get('database', 'smart_home'),
            charset=db_config.get('charset', 'utf8mb4'),
            cursorclass=DictCursor,
            autocommit=True,
            connect_timeout=5
        )
        return connection
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return None


def query_xiaomi_credentials(system_user_id: int) -> Optional[Dict[str, Any]]:
    """从数据库查询小米凭证"""
    connection = get_database_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            # 从 xiaomi_account 表查询
            # 注意：StarRocks DUPLICATE KEY 表，直接取最新记录（不判断 is_active）
            sql = """
                SELECT service_token, ssecurity, xiaomi_user_id, server, xiaomi_username
                FROM xiaomi_account 
                WHERE system_user_id = %s
                ORDER BY updated_at DESC 
                LIMIT 1
            """
            logger.info(f"执行查询: system_user_id={system_user_id}")
            cursor.execute(sql, (system_user_id,))
            result = cursor.fetchone()
            
            if result:
                logger.info(f"✅ 查询到凭证: xiaomi_username={result.get('xiaomi_username', 'N/A')}")
            else:
                logger.warning(f"⚠️ 未查询到凭证: system_user_id={system_user_id}")
            
            return result
    except Exception as e:
        logger.error(f"查询小米凭证失败: {e}", exc_info=True)
        return None
    finally:
        connection.close()


async def _fetch_user_devices(
    system_user_id: int,
    server: Optional[str] = None
) -> str:
    """
    内部函数：获取用户的所有米家设备列表（供其他函数调用）
    """
    try:
        logger.info(f"查询用户 {system_user_id} 的设备列表")
        
        # 1. 查询用户凭证
        credentials = query_xiaomi_credentials(system_user_id)
        if not credentials:
            return json.dumps({
                "success": False,
                "message": "未找到小米账号绑定信息，请先绑定小米账号",
            }, ensure_ascii=False, indent=2)
        
        # 2. 创建临时connector
        connector = XiaomiCloudConnector("", "")
        connector._serviceToken = credentials["service_token"]
        connector._ssecurity = credentials["ssecurity"]
        connector.userId = credentials["xiaomi_user_id"]
        
        # 使用指定的server或数据库中的server
        current_server = server or credentials.get("server", "cn")
        
        # 3. 获取所有家庭
        all_homes = []
        homes_result = connector.get_homes(current_server)
        
        if homes_result and homes_result.get("code") == 0:
            for h in homes_result['result']['homelist']:
                all_homes.append({
                    'home_id': h['id'],
                    'home_name': h.get('name', '未命名家庭'),
                    'home_owner': connector.userId
                })
        
        # 获取共享的家庭
        dev_cnt_result = connector.get_dev_cnt(current_server)
        if dev_cnt_result and dev_cnt_result.get("code") == 0:
            share_families = dev_cnt_result.get("result", {}).get("share", {}).get("share_family", [])
            for h in share_families:
                all_homes.append({
                    'home_id': h['home_id'],
                    'home_name': h.get('home_name', '共享家庭'),
                    'home_owner': h['home_owner']
                })
        
        # 4. 获取每个家庭的设备
        all_devices = []
        for home in all_homes:
            devices_result = connector.get_devices(current_server, home['home_id'], home['home_owner'])
            
            if devices_result and devices_result.get("code") == 0:
                device_info = devices_result.get("result", {}).get("device_info", [])
                
                for device in device_info:
                    device_data = {
                        "home_id": home['home_id'],
                        "home_name": home['home_name'],
                        "name": device.get("name", "未命名设备"),
                        "did": device.get("did", ""),
                        "model": device.get("model", ""),
                        "token": device.get("token", ""),
                        "mac": device.get("mac", ""),
                        "localip": device.get("localip", ""),
                        "parent_id": device.get("parent_id", ""),
                        "parent_model": device.get("parent_model", ""),
                        "show_mode": device.get("show_mode", 0),
                        "isOnline": device.get("isOnline", False),
                        "rssi": device.get("rssi", 0),
                    }
                    all_devices.append(device_data)
        
        logger.info(f"成功获取 {len(all_devices)} 个设备")
        
        return json.dumps({
            "success": True,
            "message": f"成功获取设备列表",
            "xiaomi_username": credentials.get("xiaomi_username", ""),
            "server": current_server,
            "total_homes": len(all_homes),
            "total_devices": len(all_devices),
            "homes": all_homes,
            "devices": all_devices,
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取设备列表异常: {str(e)}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": f"获取设备列表异常: {str(e)}",
        }, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_user_devices(
    system_user_id: int,
    server: Optional[str] = None
) -> str:
    """
    获取用户的所有米家设备列表
    
    参数：
        system_user_id: 系统用户ID（必填）
        server: 服务器区域（可选），默认使用数据库中保存的区域，可选值：cn, de, us, ru, tw, sg, in, i2
    
    返回：
        包含所有设备信息的JSON字符串，包括：
        - 设备名称 (name)
        - 设备ID (did)
        - 设备型号 (model)
        - 设备Token (token)
        - 设备IP地址 (localip)
        - 设备MAC地址 (mac)
        - 在线状态 (isOnline)
        - 所属家庭 (home_name, home_id)
    """
    return await _fetch_user_devices(system_user_id, server)


@mcp.tool()
async def get_device_by_name(
    system_user_id: int,
    device_name: str,
    server: Optional[str] = None
) -> str:
    """
    根据设备名称查询设备信息（支持模糊匹配）
    
    参数：
        system_user_id: 系统用户ID（必填）
        device_name: 设备名称（支持模糊匹配，如"空调"可以匹配"客厅空调"）
        server: 服务器区域（可选）
    
    返回：
        匹配的设备信息列表（JSON字符串）
    """
    try:
        # 先获取所有设备
        all_devices_result = await _fetch_user_devices(system_user_id, server)
        all_devices_data = json.loads(all_devices_result)
        
        if not all_devices_data.get("success"):
            return all_devices_result
        
        # 过滤匹配的设备（不区分大小写）
        devices = all_devices_data.get("devices", [])
        matched_devices = [
            device for device in devices 
            if device_name.lower() in device.get("name", "").lower()
        ]
        
        if not matched_devices:
            return json.dumps({
                "success": False,
                "message": f"未找到名称包含 '{device_name}' 的设备",
            }, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "success": True,
            "message": f"找到 {len(matched_devices)} 个匹配的设备",
            "query": device_name,
            "matched_count": len(matched_devices),
            "devices": matched_devices,
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"根据名称查询设备异常: {str(e)}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": f"查询设备异常: {str(e)}",
        }, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_device_by_model(
    system_user_id: int,
    model: str,
    server: Optional[str] = None
) -> str:
    """
    根据设备型号查询设备信息
    
    参数：
        system_user_id: 系统用户ID（必填）
        model: 设备型号（如：lumi.acpartner.mcn02）
        server: 服务器区域（可选）
    
    返回：
        匹配的设备信息列表（JSON字符串）
    """
    try:
        # 先获取所有设备
        all_devices_result = await _fetch_user_devices(system_user_id, server)
        all_devices_data = json.loads(all_devices_result)
        
        if not all_devices_data.get("success"):
            return all_devices_result
        
        # 过滤匹配的设备
        devices = all_devices_data.get("devices", [])
        matched_devices = [
            device for device in devices 
            if model.lower() in device.get("model", "").lower()
        ]
        
        if not matched_devices:
            return json.dumps({
                "success": False,
                "message": f"未找到型号为 '{model}' 的设备",
            }, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "success": True,
            "message": f"找到 {len(matched_devices)} 个匹配的设备",
            "query_model": model,
            "matched_count": len(matched_devices),
            "devices": matched_devices,
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"根据型号查询设备异常: {str(e)}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": f"查询设备异常: {str(e)}",
        }, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_online_devices(
    system_user_id: int,
    server: Optional[str] = None
) -> str:
    """
    获取所有在线的设备
    
    参数：
        system_user_id: 系统用户ID（必填）
        server: 服务器区域（可选）
    
    返回：
        在线设备信息列表（JSON字符串）
    """
    try:
        # 先获取所有设备
        all_devices_result = await _fetch_user_devices(system_user_id, server)
        all_devices_data = json.loads(all_devices_result)
        
        if not all_devices_data.get("success"):
            return all_devices_result
        
        # 过滤在线设备
        devices = all_devices_data.get("devices", [])
        online_devices = [
            device for device in devices 
            if device.get("isOnline", False)
        ]
        
        return json.dumps({
            "success": True,
            "message": f"找到 {len(online_devices)} 个在线设备",
            "total_devices": len(devices),
            "online_count": len(online_devices),
            "offline_count": len(devices) - len(online_devices),
            "devices": online_devices,
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取在线设备异常: {str(e)}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": f"查询设备异常: {str(e)}",
        }, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_device_count(
    system_user_id: int,
    server: Optional[str] = None
) -> str:
    """
    获取用户的设备统计信息
    
    参数：
        system_user_id: 系统用户ID（必填）
        server: 服务器区域（可选）
    
    返回：
        设备统计信息（JSON字符串），包括：
        - 总设备数
        - 在线设备数
        - 离线设备数
        - 各型号设备数量
        - 各家庭设备数量
    """
    try:
        # 先获取所有设备
        all_devices_result = await _fetch_user_devices(system_user_id, server)
        all_devices_data = json.loads(all_devices_result)
        
        if not all_devices_data.get("success"):
            return all_devices_result
        
        devices = all_devices_data.get("devices", [])
        
        # 统计信息
        total_devices = len(devices)
        online_devices = sum(1 for d in devices if d.get("isOnline", False))
        offline_devices = total_devices - online_devices
        
        # 按型号统计
        model_stats = {}
        for device in devices:
            model = device.get("model", "未知型号")
            if model not in model_stats:
                model_stats[model] = 0
            model_stats[model] += 1
        
        # 按家庭统计
        home_stats = {}
        for device in devices:
            home_name = device.get("home_name", "未知家庭")
            if home_name not in home_stats:
                home_stats[home_name] = 0
            home_stats[home_name] += 1
        
        return json.dumps({
            "success": True,
            "message": "统计信息获取成功",
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": offline_devices,
            "total_homes": all_devices_data.get("total_homes", 0),
            "model_statistics": model_stats,
            "home_statistics": home_stats,
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取设备统计异常: {str(e)}", exc_info=True)
        return json.dumps({
            "success": False,
            "message": f"获取统计信息异常: {str(e)}",
        }, ensure_ascii=False, indent=2)


# 主函数，用于启动 MCP 服务器
if __name__ == "__main__":
    # 运行 MCP 服务器
    mcp.run()

