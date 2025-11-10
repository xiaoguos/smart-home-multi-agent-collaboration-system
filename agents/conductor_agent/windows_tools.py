"""
Windows系统控制工具
提供Windows桌面自动化功能
"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'app', 'backend-python'))

logger = logging.getLogger(__name__)


class WindowsAppArgs(BaseModel):
    """Windows应用管理参数"""
    action: str = Field(..., description="操作类型：launch(启动), switch(切换)")
    app_name: str = Field(..., description="应用程序名称，如'notepad','chrome','explorer'")


class WindowsPowerShellArgs(BaseModel):
    """PowerShell命令参数"""
    command: str = Field(..., description="要执行的PowerShell命令")


class WindowsShortcutArgs(BaseModel):
    """快捷键参数"""
    shortcut: str = Field(..., description="快捷键组合，如'ctrl+c','win+e'")


@tool("manage_windows_app", args_schema=WindowsAppArgs, description="管理Windows应用（启动/切换）")
def manage_windows_app(action: str, app_name: str) -> str:
    """管理Windows应用程序"""
    try:
        from services.windows_mcp_service import get_windows_mcp_service
        import asyncio
        
        mcp_service = get_windows_mcp_service()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if action == "launch":
            result = loop.run_until_complete(mcp_service.launch_app(app_name))
        elif action == "switch":
            result = loop.run_until_complete(mcp_service.switch_app(app_name))
        else:
            return f"❌ 不支持的操作: {action}"
            
        loop.close()
        
        if result and result.get("success"):
            return f"✅ Windows应用操作成功：{result.get('data', '')}"
        else:
            return f"❌ 操作失败：{result.get('message', '未知错误')}"
        
    except Exception as e:
        logger.error(f"Windows应用管理失败: {e}", exc_info=True)
        return f"❌ 发生错误：{str(e)}"


@tool("execute_powershell_command", args_schema=WindowsPowerShellArgs, description="执行PowerShell命令")
def execute_powershell_command(command: str) -> str:
    """执行PowerShell命令"""
    try:
        from services.windows_mcp_service import get_windows_mcp_service
        import asyncio
        
        mcp_service = get_windows_mcp_service()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(mcp_service.execute_powershell(command))
        loop.close()
        
        if result and result.get("success"):
            return f"✅ PowerShell执行成功：\n\n{result.get('data', '')}"
        else:
            return f"❌ 执行失败：{result.get('message', '未知错误')}"
        
    except Exception as e:
        logger.error(f"PowerShell执行失败: {e}", exc_info=True)
        return f"❌ 发生错误：{str(e)}"


@tool("execute_windows_shortcut", args_schema=WindowsShortcutArgs, description="执行Windows快捷键")
def execute_windows_shortcut(shortcut: str) -> str:
    """执行Windows快捷键"""
    try:
        from services.windows_mcp_service import get_windows_mcp_service
        import asyncio
        
        mcp_service = get_windows_mcp_service()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(mcp_service.shortcut(shortcut))
        loop.close()
        
        if result and result.get("success"):
            return f"✅ 快捷键执行成功：{result.get('data', '')}"
        else:
            return f"❌ 执行失败：{result.get('message', '未知错误')}"
        
    except Exception as e:
        logger.error(f"快捷键执行失败: {e}", exc_info=True)
        return f"❌ 发生错误：{str(e)}"


__all__ = ['manage_windows_app', 'execute_powershell_command', 'execute_windows_shortcut']

