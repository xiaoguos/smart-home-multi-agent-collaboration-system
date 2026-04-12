"""
主入口点 - 用于 `uv run .` 或 `python -m conductor_agent` 启动服务
家庭管家Agent
"""

import sys
from pathlib import Path
import click
import logging
import uvicorn
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
import httpx
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)

# 确保当前目录和父目录在 Python 路径中
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from executor import ConductorAgentExecutor
from agent import ConductorAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", "host", default=None, help="服务主机地址（默认从 .env/config.yaml 读取）")
@click.option("--port", "port", default=None, type=int, help="服务端口（默认从 .env/config.yaml 读取）")
@click.option("--debug", "debug_mode", is_flag=True, default=False, help="启用 debug 模式（兼容 PyCharm debugger）")
def main(host, port, debug_mode):
    """Starts the Conductor Agent server."""
    try:
        # 从配置文件读取 host 和 port（如果命令行未指定）
        if host is None or port is None:
            from config_loader import get_config_loader
            config_loader = get_config_loader(strict_mode=False)
            default_host,             default_port = config_loader.get_agent_host_port('conductor')
            host = host or default_host
            port = port or default_port
        
        capabilities = AgentCapabilities(
            push_notifications=False,
            state_transition_history=False,
            streaming=False,
        )
        skill = AgentSkill(
            id="smart_home_management",
            name="Smart Home Management",
            description="智能家居总管理系统，协调和管理所有智能设备代理",
            tags=["smart home", "home automation", "agent management", "device control"],
            examples=[
                "查看所有可用代理",
                "控制空调温度",
                "检查系统状态",
                "管理空气净化器",
                "分析我的使用习惯",
                "获取个性化建议",
            ],
        )
        agent_card = AgentCard(
            name="Conductor Agent",
            description="智能家居总管理助手，负责协调和管理所有智能设备代理",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=ConductorAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=ConductorAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        # --8<-- [start:DefaultRequestHandler]
        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(
            httpx_client=httpx_client, config_store=push_config_store
        )
        request_handler = DefaultRequestHandler(
            agent_executor=ConductorAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=push_config_store,
            push_sender=push_sender,
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        # 检测是否在 PyCharm debugger 中运行
        is_debugging = sys.gettrace() is not None or debug_mode
        
        if is_debugging:
            # PyCharm Debug 模式：使用兼容的方式启动
            import asyncio
            config = uvicorn.Config(
                server.build(), 
                host=host, 
                port=port,
                log_level="info"
            )
            server_instance = uvicorn.Server(config)
            asyncio.run(server_instance.serve())
        else:
            # 正常模式：使用标准方式
            uvicorn.run(server.build(), host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
