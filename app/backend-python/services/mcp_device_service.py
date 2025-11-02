"""
MCP 设备服务
封装 MCP 设备查询服务的调用，供后端 API 使用
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class MCPDeviceService:
    """MCP 设备服务类"""
    
    def __init__(self):
        """初始化 MCP 设备服务"""
        # 计算 MCP 服务路径
        # 当前文件: app/backend-python/services/mcp_device_service.py
        # 目标路径: mcp/device_query_mcp.py
        current_dir = Path(__file__).parent  # app/backend-python/services
        backend_dir = current_dir.parent      # app/backend-python
        app_dir = backend_dir.parent          # app
        project_root = app_dir.parent         # project root
        self.mcp_path = project_root / "mcp" / "device_query_mcp.py"
        
        logger.info(f"MCP 服务路径: {self.mcp_path}")
        
        if not self.mcp_path.exists():
            logger.warning(f"MCP 服务文件不存在: {self.mcp_path}")
        
        # MCP 依赖检查
        self.mcp_available = self._check_mcp_available()
    
    def _check_mcp_available(self) -> bool:
        """检查 MCP 是否可用"""
        # 1. 检查文件是否存在
        if not self.mcp_path.exists():
            logger.error(f"❌ MCP 服务文件不存在: {self.mcp_path}")
            return False
        
        # 2. 检查依赖是否已安装
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            logger.info("✅ MCP 依赖检查通过")
            return True
        except ImportError as e:
            logger.error(f"❌ MCP 依赖未安装: {e}")
            return False
        
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具返回的结果（JSON 格式），如果MCP不可用返回包含错误信息的字典
        """
        # 预检查：MCP 是否可用
        if not self.mcp_available:
            if not self.mcp_path.exists():
                logger.error(f"开发错误：MCP 服务文件不存在: {self.mcp_path}")
            else:
                logger.error("开发错误：MCP 依赖未安装（pip install fastmcp）")
            
            return {
                "success": False,
                "message": "请先检查设备查询服务是否启动。"
            }
        
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            logger.info(f"✅ 调用 MCP 工具: {tool_name}, 参数: {arguments}")
            
            # 创建 MCP 客户端
            server_params = StdioServerParameters(
                command="python",
                args=[str(self.mcp_path)],
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 初始化
                    await session.initialize()
                    
                    # 调用工具
                    result = await session.call_tool(tool_name, arguments=arguments)
                    
                    # 解析结果
                    result_text = result.content[0].text if hasattr(result, 'content') else str(result)
                    return json.loads(result_text)
                    
        except ImportError as e:
            logger.error(f"开发错误：MCP 模块未安装: {e}")
            return {
                "success": False,
                "message": "请先检查设备查询服务是否启动。"
            }
        except Exception as e:
            logger.error(f"MCP 服务调用失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": "请先检查设备查询服务是否启动。"
            }
    
    def _call_mcp_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        同步方式调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具返回的结果（JSON 格式）
        """
        try:
            # 获取或创建事件循环
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 运行异步函数
            return loop.run_until_complete(self._call_mcp_tool(tool_name, arguments))
        except Exception as e:
            logger.error(f"同步调用 MCP 工具失败: {e}")
            return None
    
    async def get_user_devices(
        self,
        system_user_id: int,
        server: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户的所有米家设备列表
        
        Args:
            system_user_id: 系统用户ID
            server: 服务器区域（可选）
            
        Returns:
            设备列表信息
        """
        arguments = {"system_user_id": system_user_id}
        if server:
            arguments["server"] = server
        
        return await self._call_mcp_tool("get_user_devices", arguments)
    
    def get_user_devices_sync(
        self,
        system_user_id: int,
        server: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户的所有米家设备列表（同步版本）
        
        Args:
            system_user_id: 系统用户ID
            server: 服务器区域（可选）
            
        Returns:
            设备列表信息
        """
        arguments = {"system_user_id": system_user_id}
        if server:
            arguments["server"] = server
        
        return self._call_mcp_tool_sync("get_user_devices", arguments)
    
    async def get_device_by_name(
        self,
        system_user_id: int,
        device_name: str,
        server: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        根据设备名称查询设备信息
        
        Args:
            system_user_id: 系统用户ID
            device_name: 设备名称（支持模糊匹配）
            server: 服务器区域（可选）
            
        Returns:
            匹配的设备信息
        """
        arguments = {
            "system_user_id": system_user_id,
            "device_name": device_name
        }
        if server:
            arguments["server"] = server
        
        return await self._call_mcp_tool("get_device_by_name", arguments)
    
    def get_device_by_name_sync(
        self,
        system_user_id: int,
        device_name: str,
        server: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        根据设备名称查询设备信息（同步版本）
        
        Args:
            system_user_id: 系统用户ID
            device_name: 设备名称（支持模糊匹配）
            server: 服务器区域（可选）
            
        Returns:
            匹配的设备信息
        """
        arguments = {
            "system_user_id": system_user_id,
            "device_name": device_name
        }
        if server:
            arguments["server"] = server
        
        return self._call_mcp_tool_sync("get_device_by_name", arguments)
    
    async def get_device_by_model(
        self,
        system_user_id: int,
        model: str,
        server: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        根据设备型号查询设备信息
        
        Args:
            system_user_id: 系统用户ID
            model: 设备型号
            server: 服务器区域（可选）
            
        Returns:
            匹配的设备信息
        """
        arguments = {
            "system_user_id": system_user_id,
            "model": model
        }
        if server:
            arguments["server"] = server
        
        return await self._call_mcp_tool("get_device_by_model", arguments)
    
    def get_device_by_model_sync(
        self,
        system_user_id: int,
        model: str,
        server: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        根据设备型号查询设备信息（同步版本）
        
        Args:
            system_user_id: 系统用户ID
            model: 设备型号
            server: 服务器区域（可选）
            
        Returns:
            匹配的设备信息
        """
        arguments = {
            "system_user_id": system_user_id,
            "model": model
        }
        if server:
            arguments["server"] = server
        
        return self._call_mcp_tool_sync("get_device_by_model", arguments)
    
    async def get_online_devices(
        self,
        system_user_id: int,
        server: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取所有在线的设备
        
        Args:
            system_user_id: 系统用户ID
            server: 服务器区域（可选）
            
        Returns:
            在线设备信息
        """
        arguments = {"system_user_id": system_user_id}
        if server:
            arguments["server"] = server
        
        return await self._call_mcp_tool("get_online_devices", arguments)
    
    def get_online_devices_sync(
        self,
        system_user_id: int,
        server: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取所有在线的设备（同步版本）
        
        Args:
            system_user_id: 系统用户ID
            server: 服务器区域（可选）
            
        Returns:
            在线设备信息
        """
        arguments = {"system_user_id": system_user_id}
        if server:
            arguments["server"] = server
        
        return self._call_mcp_tool_sync("get_online_devices", arguments)
    
    async def get_device_count(
        self,
        system_user_id: int,
        server: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户的设备统计信息
        
        Args:
            system_user_id: 系统用户ID
            server: 服务器区域（可选）
            
        Returns:
            设备统计信息
        """
        arguments = {"system_user_id": system_user_id}
        if server:
            arguments["server"] = server
        
        return await self._call_mcp_tool("get_device_count", arguments)
    
    def get_device_count_sync(
        self,
        system_user_id: int,
        server: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户的设备统计信息（同步版本）
        
        Args:
            system_user_id: 系统用户ID
            server: 服务器区域（可选）
            
        Returns:
            设备统计信息
        """
        arguments = {"system_user_id": system_user_id}
        if server:
            arguments["server"] = server
        
        return self._call_mcp_tool_sync("get_device_count", arguments)


# 全局实例
_mcp_device_service = None


def get_mcp_device_service() -> MCPDeviceService:
    """获取 MCP 设备服务实例（单例模式）"""
    global _mcp_device_service
    if _mcp_device_service is None:
        _mcp_device_service = MCPDeviceService()
    return _mcp_device_service

