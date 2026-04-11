import asyncio
import json
import logging
import os
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class MCPDeviceService:
    """MCP 设备服务类"""
    
    def __init__(self):
        """初始化 MCP 设备服务"""
        # 通过已运行的 MCP Gateway（SSE）访问下游 device_query 服务
        self.gateway_url = (
            os.environ.get("MCP_GATEWAY_SSE_URL", "http://127.0.0.1:8099/sse").strip()
            or "http://127.0.0.1:8099/sse"
        )
        self.gateway_tool_name = (
            os.environ.get("MCP_GATEWAY_PROXY_TOOL", "call_gateway_service_tool").strip()
            or "call_gateway_service_tool"
        )
        self.target_service_name = (
            os.environ.get("MCP_DEVICE_SERVICE_NAME", "device_query").strip()
            or "device_query"
        )
        logger.info(
            "MCP 网关配置: url=%s, proxy_tool=%s, target_service=%s",
            self.gateway_url,
            self.gateway_tool_name,
            self.target_service_name,
        )
        
        # MCP 依赖检查
        self.mcp_available = self._check_mcp_available()
    
    def _check_mcp_available(self) -> bool:
        """检查 MCP 是否可用"""
        # 检查网关客户端依赖
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client

            _ = (ClientSession, sse_client)
            logger.info("✅ MCP 网关客户端依赖检查通过")
            return True
        except ImportError as e:
            logger.error(f"❌ MCP 依赖未安装: {e}")
            return False

    @staticmethod
    def _extract_text_from_tool_result(result: Any) -> str:
        """从 MCP tool result 中提取文本内容。"""
        if hasattr(result, "content") and result.content:
            part = result.content[0]
            if hasattr(part, "text") and isinstance(part.text, str):
                return part.text
        return str(result)
        
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
            logger.error("开发错误：请安装官方 MCP Python SDK（pip install mcp）")
            
            return {
                "success": False,
                "message": "MCP 客户端依赖缺失，请安装 mcp。"
            }
        
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client
            
            logger.info(
                "✅ 通过 MCP 网关调用工具: service=%s, tool=%s, args=%s",
                self.target_service_name,
                tool_name,
                arguments,
            )
            
            gateway_args = {
                "service_name": self.target_service_name,
                "tool_name": tool_name,
                "arguments_json": json.dumps(arguments, ensure_ascii=False),
            }
            
            async with sse_client(self.gateway_url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        self.gateway_tool_name,
                        arguments=gateway_args,
                    )

            payload_text = self._extract_text_from_tool_result(result)
            try:
                gateway_payload = json.loads(payload_text)
            except json.JSONDecodeError:
                logger.error("MCP 网关返回非 JSON: %s", payload_text)
                return {"success": False, "message": "MCP网关返回格式异常（非JSON）"}

            if not gateway_payload.get("success"):
                return {
                    "success": False,
                    "message": gateway_payload.get("message", "MCP网关调用失败"),
                }

            wrapped = gateway_payload.get("result", {}) if isinstance(gateway_payload, dict) else {}
            parsed = wrapped.get("parsed") if isinstance(wrapped, dict) else None

            # 理想路径：下游工具返回 JSON 对象
            if isinstance(parsed, dict):
                return parsed

            # 兼容路径：返回字符串 JSON
            if isinstance(parsed, str):
                try:
                    parsed_obj = json.loads(parsed)
                    if isinstance(parsed_obj, dict):
                        return parsed_obj
                    return {"success": True, "data": parsed_obj}
                except json.JSONDecodeError:
                    return {"success": True, "data": parsed}

            text_fallback = wrapped.get("text") if isinstance(wrapped, dict) else None
            if isinstance(text_fallback, str) and text_fallback.strip():
                try:
                    parsed_obj = json.loads(text_fallback)
                    if isinstance(parsed_obj, dict):
                        return parsed_obj
                except json.JSONDecodeError:
                    pass

            return {"success": False, "message": "MCP网关返回结果缺少可解析数据"}
                    
        except ImportError as e:
            logger.error(f"开发错误：MCP 模块未安装: {e}")
            return {
                "success": False,
                "message": "MCP 客户端依赖缺失，请安装 mcp。"
            }
        except Exception as e:
            logger.error(f"MCP 网关调用失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"MCP网关调用失败: {str(e)}"
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

