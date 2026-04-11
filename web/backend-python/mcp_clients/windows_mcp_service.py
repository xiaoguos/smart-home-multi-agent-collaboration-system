"""
Windows MCP 服务
封装Windows MCP服务的调用，供后端 API 和 Agent 使用
提供Windows系统自动化功能
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Literal

logger = logging.getLogger(__name__)


class WindowsMCPService:
    """Windows MCP 服务类"""

    def __init__(self):
        """初始化Windows MCP 服务"""
        current_dir = Path(__file__).parent
        backend_dir = current_dir.parent
        app_dir = backend_dir.parent
        project_root = app_dir.parent
        self.mcp_path = project_root / "mcp" / "Windows-MCP" / "main.py"

        logger.info(f"Windows MCP 服务路径: {self.mcp_path}")

        if not self.mcp_path.exists():
            logger.warning(f"Windows MCP 服务文件不存在: {self.mcp_path}")

        self.mcp_available = self._check_mcp_available()

    def _check_mcp_available(self) -> bool:
        """检查 MCP 是否可用"""
        if not self.mcp_path.exists():
            logger.error(f"❌ Windows MCP 服务文件不存在: {self.mcp_path}")
            return False

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            logger.info("✅ Windows MCP 依赖检查通过")
            return True
        except ImportError as e:
            logger.error(f"❌ Windows MCP 依赖未安装: {e}")
            return False

    async def _call_mcp_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """调用Windows MCP 工具"""
        if not self.mcp_available:
            return {"success": False, "message": "Windows MCP服务不可用"}

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            logger.info(f"✅ 调用Windows MCP 工具: {tool_name}, 参数: {arguments}")

            mcp_dir = self.mcp_path.parent
            
            server_params = StdioServerParameters(
                command="uv",
                args=["--directory", str(mcp_dir), "run", "main.py"],
                env=os.environ.copy(),
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=arguments)

                    if hasattr(result, "content") and len(result.content) > 0:
                        result_text = result.content[0].text
                        return {"success": True, "data": result_text}
                    else:
                        return {"success": True, "data": str(result)}

        except Exception as e:
            logger.error(f"Windows MCP 服务调用失败: {e}", exc_info=True)
            return {"success": False, "message": f"MCP服务调用失败: {str(e)}"}

    # ==================== 应用管理 ====================
    async def launch_app(self, app_name: str) -> Optional[Dict[str, Any]]:
        """启动应用程序"""
        return await self._call_mcp_tool("App-Tool", {"mode": "launch", "name": app_name})

    async def switch_app(self, app_name: str) -> Optional[Dict[str, Any]]:
        """切换到指定应用"""
        return await self._call_mcp_tool("App-Tool", {"mode": "switch", "name": app_name})

    # ==================== PowerShell ====================
    async def execute_powershell(self, command: str) -> Optional[Dict[str, Any]]:
        """执行PowerShell命令"""
        return await self._call_mcp_tool("Powershell-Tool", {"command": command})

    # ==================== 桌面状态 ====================
    async def get_desktop_state(self, use_vision: bool = False) -> Optional[Dict[str, Any]]:
        """获取桌面状态"""
        return await self._call_mcp_tool("State-Tool", {"use_vision": use_vision})

    # ==================== 快捷键 ====================
    async def shortcut(self, shortcut: str) -> Optional[Dict[str, Any]]:
        """执行快捷键"""
        return await self._call_mcp_tool("Shortcut-Tool", {"shortcut": shortcut})


# 全局实例
_windows_mcp_service = None

def get_windows_mcp_service() -> WindowsMCPService:
    """获取Windows MCP 服务实例（单例模式）"""
    global _windows_mcp_service
    if _windows_mcp_service is None:
        _windows_mcp_service = WindowsMCPService()
    return _windows_mcp_service

