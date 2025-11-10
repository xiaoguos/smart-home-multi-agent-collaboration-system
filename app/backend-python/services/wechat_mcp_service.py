"""
微信 MCP 服务
封装微信MCP服务的调用，供后端 API 和 Agent 使用
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class WechatMCPService:
    """微信 MCP 服务类"""

    def __init__(self):
        """初始化微信 MCP 服务"""
        # 计算 MCP 服务路径
        # 当前文件: app/backend-python/services/wechat_mcp_service.py
        # 目标路径: mcp/mcp_server_wechat/mcp_server_wechat/__main__.py
        current_dir = Path(__file__).parent  # app/backend-python/services
        backend_dir = current_dir.parent  # app/backend-python
        app_dir = backend_dir.parent  # app
        project_root = app_dir.parent  # project root
        self.mcp_path = project_root / "mcp" / "mcp_server_wechat" / "mcp_server_wechat" / "__main__.py"

        logger.info(f"微信 MCP 服务路径: {self.mcp_path}")

        if not self.mcp_path.exists():
            logger.warning(f"微信 MCP 服务文件不存在: {self.mcp_path}")

        # MCP 依赖检查
        self.mcp_available = self._check_mcp_available()
        
        # 默认聊天记录保存路径
        self.default_folder_path = str(project_root / "data" / "wechat_history")

    def _check_mcp_available(self) -> bool:
        """检查 MCP 是否可用"""
        # 1. 检查文件是否存在
        if not self.mcp_path.exists():
            logger.error(f"❌ 微信 MCP 服务文件不存在: {self.mcp_path}")
            return False

        # 2. 检查依赖是否已安装
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            logger.info("✅ 微信 MCP 依赖检查通过")
            return True
        except ImportError as e:
            logger.error(f"❌ 微信 MCP 依赖未安装: {e}")
            return False

    async def _call_mcp_tool(
        self, tool_name: str, arguments: Dict[str, Any], folder_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        调用微信 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            folder_path: 聊天记录保存路径（可选）

        Returns:
            工具返回的结果（JSON 格式），如果MCP不可用返回包含错误信息的字典
        """
        # 预检查：MCP 是否可用
        if not self.mcp_available:
            if not self.mcp_path.exists():
                logger.error(f"开发错误：微信 MCP 服务文件不存在: {self.mcp_path}")
            else:
                logger.error("开发错误：微信 MCP 依赖未安装（pip install mcp）")

            return {"success": False, "message": "微信MCP服务不可用，请检查服务配置"}

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            logger.info(f"✅ 调用微信 MCP 工具: {tool_name}, 参数: {arguments}")

            # 准备命令参数和环境变量
            folder_path = folder_path or self.default_folder_path
            
            # 直接运行MCP服务脚本的 __main__.py
            mcp_package_dir = self.mcp_path.parent  # mcp_server_wechat 目录
            mcp_main_script = mcp_package_dir / "__main__.py"
            
            # 准备环境变量，添加 PYTHONPATH
            env = os.environ.copy()
            # 将 mcp_server_wechat 的父目录添加到 PYTHONPATH
            mcp_parent_dir = str(mcp_package_dir.parent)  # mcp/mcp_server_wechat 的父目录
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = f"{mcp_parent_dir}{os.pathsep}{env['PYTHONPATH']}"
            else:
                env['PYTHONPATH'] = mcp_parent_dir
            
            logger.info(f"微信MCP脚本路径: {mcp_main_script}")
            logger.info(f"PYTHONPATH: {env.get('PYTHONPATH', 'Not set')}")
            
            # 创建 MCP 客户端
            server_params = StdioServerParameters(
                command="python",
                args=[
                    str(mcp_main_script),
                    f"--folder-path={folder_path}"
                ],
                env=env,
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 初始化
                    await session.initialize()

                    # 调用工具
                    result = await session.call_tool(tool_name, arguments=arguments)

                    # 解析结果
                    if hasattr(result, "content") and len(result.content) > 0:
                        result_text = result.content[0].text
                        # 尝试解析为JSON，如果失败就返回原始文本
                        try:
                            return {"success": True, "data": json.loads(result_text)}
                        except json.JSONDecodeError:
                            return {"success": True, "data": result_text}
                    else:
                        return {"success": True, "data": str(result)}

        except ImportError as e:
            logger.error(f"开发错误：微信 MCP 模块未安装: {e}")
            return {"success": False, "message": "微信MCP服务不可用"}
        except Exception as e:
            logger.error(f"微信 MCP 服务调用失败: {e}", exc_info=True)
            return {"success": False, "message": f"MCP服务调用失败: {str(e)}"}

    # ==================== 微信功能接口 ====================

    async def get_chat_history(
        self, to_user: str, target_date: str, folder_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取微信聊天记录

        Args:
            to_user: 好友或群聊备注或昵称
            target_date: 目标日期，格式为YY/M/D，如25/3/22
            folder_path: 聊天记录保存路径（可选）

        Returns:
            聊天记录结果
        """
        arguments = {
            "to_user": to_user,
            "target_date": target_date
        }

        return await self._call_mcp_tool("wechat_get_chat_history", arguments, folder_path)

    async def send_message(
        self, to_user: str, message: str
    ) -> Optional[Dict[str, Any]]:
        """
        发送单条消息给单个好友

        Args:
            to_user: 好友或群聊备注或昵称
            message: 要发送的消息

        Returns:
            发送结果
        """
        arguments = {
            "to_user": to_user,
            "message": message
        }

        return await self._call_mcp_tool("wechat_send_message", arguments)

    async def send_multiple_messages(
        self, to_user: str, messages: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        发送多条消息给单个好友

        Args:
            to_user: 好友或群聊备注或昵称
            messages: 要发送的消息列表

        Returns:
            发送结果
        """
        arguments = {
            "to_user": to_user,
            "messages": messages
        }

        return await self._call_mcp_tool("wechat_send_multiple_messages", arguments)

    async def send_to_multiple_friends(
        self, to_users: List[str], message: str
    ) -> Optional[Dict[str, Any]]:
        """
        发送消息给多个好友

        Args:
            to_users: 好友或群聊备注或昵称列表
            message: 要发送的消息（单条消息或逗号分隔的多条消息）

        Returns:
            发送结果
        """
        arguments = {
            "to_user": to_users,
            "message": message
        }

        return await self._call_mcp_tool("wechat_send_to_multiple_friends", arguments)


# 全局实例
_wechat_mcp_service = None


def get_wechat_mcp_service() -> WechatMCPService:
    """获取微信 MCP 服务实例（单例模式）"""
    global _wechat_mcp_service
    if _wechat_mcp_service is None:
        _wechat_mcp_service = WechatMCPService()
    return _wechat_mcp_service

