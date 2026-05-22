import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class DidaMCPService:
    """滴答清单 MCP 服务类"""

    def __init__(self):
        """初始化滴答清单 MCP 服务"""
        # 计算 MCP 服务路径
        # 当前文件: app/backend-python/services/dida_mcp_service.py
        # 目标路径: mcp/didatodolist-mcp/main.py
        current_dir = Path(__file__).parent  # app/backend-python/services
        backend_dir = current_dir.parent  # app/backend-python
        app_dir = backend_dir.parent  # app
        project_root = app_dir.parent  # project root
        self.mcp_path = project_root / "mcp_server" / "didatodolist-mcp" / "main.py"

        logger.info(f"滴答清单 MCP 服务路径: {self.mcp_path}")

        if not self.mcp_path.exists():
            logger.warning(f"滴答清单 MCP 服务文件不存在: {self.mcp_path}")

        # MCP 依赖检查
        self.mcp_available = self._check_mcp_available()

    def _check_mcp_available(self) -> bool:
        """检查 MCP 是否可用"""
        # 1. 检查文件是否存在
        if not self.mcp_path.exists():
            logger.error(f"❌ 滴答清单 MCP 服务文件不存在: {self.mcp_path}")
            return False

        # 2. 检查依赖是否已安装
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            logger.info("✅ 滴答清单 MCP 依赖检查通过")
            return True
        except ImportError as e:
            logger.error(f"❌ 滴答清单 MCP 依赖未安装: {e}")
            return False

    async def _call_mcp_tool(
        self, tool_name: str, arguments: Dict[str, Any], env_vars: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        调用滴答清单 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            env_vars: 环境变量（用于传递access_token等）

        Returns:
            工具返回的结果（JSON 格式），如果MCP不可用返回包含错误信息的字典
        """
        # 预检查：MCP 是否可用
        if not self.mcp_available:
            if not self.mcp_path.exists():
                logger.error(f"开发错误：滴答清单 MCP 服务文件不存在: {self.mcp_path}")
            else:
                logger.error("开发错误：请安装官方 MCP Python SDK（pip install mcp）")

            return {"success": False, "message": "请先检查滴答清单MCP服务是否启动。"}

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            logger.info(f"✅ 调用滴答清单 MCP 工具: {tool_name}, 参数: {arguments}")

            # 准备环境变量
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            # 创建 MCP 客户端
            server_params = StdioServerParameters(
                command="python",
                args=[str(self.mcp_path)],
                env=env,
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 初始化
                    await session.initialize()

                    # 调用工具
                    result = await session.call_tool(tool_name, arguments=arguments)

                    # 解析结果
                    result_text = (
                        result.content[0].text if hasattr(result, "content") else str(result)
                    )
                    return json.loads(result_text)

        except ImportError as e:
            logger.error(f"开发错误：滴答清单 MCP 模块未安装: {e}")
            return {"success": False, "message": "请先检查滴答清单MCP服务是否启动。"}
        except Exception as e:
            logger.error(f"滴答清单 MCP 服务调用失败: {e}", exc_info=True)
            return {"success": False, "message": f"MCP服务调用失败: {str(e)}"}

    def _call_mcp_tool_sync(
        self, tool_name: str, arguments: Dict[str, Any], env_vars: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        同步方式调用滴答清单 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            env_vars: 环境变量

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
            return loop.run_until_complete(self._call_mcp_tool(tool_name, arguments, env_vars))
        except Exception as e:
            logger.error(f"同步调用滴答清单 MCP 工具失败: {e}")
            return None

    # ==================== 任务管理相关接口 ====================

    async def create_task(
        self, access_token: str, title: str, content: str = "", project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        创建任务

        Args:
            access_token: 访问令牌
            title: 任务标题
            content: 任务内容
            project_id: 项目ID（可选）

        Returns:
            任务创建结果
        """
        arguments = {"title": title}
        if content:
            arguments["content"] = content
        if project_id:
            arguments["project_id"] = project_id

        env_vars = {"DIDA_ACCESS_TOKEN": access_token}

        return await self._call_mcp_tool("create_task", arguments, env_vars)

    async def get_tasks(
        self, access_token: str, project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取任务列表

        Args:
            access_token: 访问令牌
            project_id: 项目ID（可选，不传则获取所有任务）

        Returns:
            任务列表
        """
        arguments = {}
        if project_id:
            arguments["project_id"] = project_id

        env_vars = {"DIDA_ACCESS_TOKEN": access_token}

        return await self._call_mcp_tool("get_tasks", arguments, env_vars)

    async def update_task(
        self, access_token: str, task_id: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        更新任务

        Args:
            access_token: 访问令牌
            task_id: 任务ID
            **kwargs: 要更新的字段（title, content, status等）

        Returns:
            更新结果
        """
        arguments = {"task_id": task_id}
        arguments.update(kwargs)

        env_vars = {"DIDA_ACCESS_TOKEN": access_token}

        return await self._call_mcp_tool("update_task", arguments, env_vars)

    async def delete_task(self, access_token: str, task_id: str) -> Optional[Dict[str, Any]]:
        """
        删除任务

        Args:
            access_token: 访问令牌
            task_id: 任务ID

        Returns:
            删除结果
        """
        arguments = {"task_id": task_id}
        env_vars = {"DIDA_ACCESS_TOKEN": access_token}

        return await self._call_mcp_tool("delete_task", arguments, env_vars)

    async def complete_task(self, access_token: str, task_id: str) -> Optional[Dict[str, Any]]:
        """
        完成任务

        Args:
            access_token: 访问令牌
            task_id: 任务ID

        Returns:
            完成结果
        """
        arguments = {"task_id": task_id}
        env_vars = {"DIDA_ACCESS_TOKEN": access_token}

        return await self._call_mcp_tool("complete_task", arguments, env_vars)

    # ==================== 项目管理相关接口 ====================

    async def get_projects(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        获取项目列表

        Args:
            access_token: 访问令牌

        Returns:
            项目列表
        """
        env_vars = {"DIDA_ACCESS_TOKEN": access_token}
        return await self._call_mcp_tool("get_projects", {}, env_vars)

    async def create_project(
        self, access_token: str, name: str, color: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        创建项目

        Args:
            access_token: 访问令牌
            name: 项目名称
            color: 项目颜色（可选）

        Returns:
            项目创建结果
        """
        arguments = {"name": name}
        if color:
            arguments["color"] = color

        env_vars = {"DIDA_ACCESS_TOKEN": access_token}

        return await self._call_mcp_tool("create_project", arguments, env_vars)

    async def update_project(
        self, access_token: str, project_id: str, **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        更新项目

        Args:
            access_token: 访问令牌
            project_id: 项目ID
            **kwargs: 要更新的字段（name, color等）

        Returns:
            更新结果
        """
        arguments = {"project_id": project_id}
        arguments.update(kwargs)

        env_vars = {"DIDA_ACCESS_TOKEN": access_token}

        return await self._call_mcp_tool("update_project", arguments, env_vars)

    async def delete_project(
        self, access_token: str, project_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        删除项目

        Args:
            access_token: 访问令牌
            project_id: 项目ID

        Returns:
            删除结果
        """
        arguments = {"project_id": project_id}
        env_vars = {"DIDA_ACCESS_TOKEN": access_token}

        return await self._call_mcp_tool("delete_project", arguments, env_vars)

    # ==================== 标签管理相关接口 ====================

    async def get_tags(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        获取标签列表

        Args:
            access_token: 访问令牌

        Returns:
            标签列表
        """
        env_vars = {"DIDA_ACCESS_TOKEN": access_token}
        return await self._call_mcp_tool("get_tags", {}, env_vars)

    # ==================== 统计分析相关接口 ====================

    async def get_task_statistics(
        self, access_token: str, project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取任务统计

        Args:
            access_token: 访问令牌
            project_id: 项目ID（可选）

        Returns:
            任务统计结果
        """
        arguments = {}
        if project_id:
            arguments["project_id"] = project_id

        env_vars = {"DIDA_ACCESS_TOKEN": access_token}

        return await self._call_mcp_tool("get_task_statistics", arguments, env_vars)


# 全局实例
_dida_mcp_service = None


def get_dida_mcp_service() -> DidaMCPService:
    """获取滴答清单 MCP 服务实例（单例模式）"""
    global _dida_mcp_service
    if _dida_mcp_service is None:
        _dida_mcp_service = DidaMCPService()
    return _dida_mcp_service

