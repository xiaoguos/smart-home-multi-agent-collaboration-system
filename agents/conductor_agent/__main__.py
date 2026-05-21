"""
主入口点 - 用于 `uv run .` 或 `python -m conductor_agent` 启动服务
家庭管家Agent
"""

import sys
import os
from pathlib import Path
import click
import logging
import uvicorn
import dotenv
from starlette.applications import Starlette
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
)
import httpx
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)

# 确保当前目录和父目录在 Python 路径中
_CURRENT_DIR = Path(__file__).resolve().parent
_PARENT_DIR = _CURRENT_DIR.parent
if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from executor import ConductorAgentExecutor
from agent import ConductorAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv.load_dotenv(dotenv_path=_CURRENT_DIR / ".env", override=True)


@click.command()
@click.option("--host", default=None, help="服务主机地址（默认从 .env 读取 AGENT_CONDUCTOR_HOST）")
@click.option("--port", default=None, type=int, help="服务端口（默认从 .env 读取 AGENT_CONDUCTOR_PORT）")
@click.option("--debug", "debug_mode", is_flag=True, default=False, help="启用 debug 模式")
def main(host=None, port=None, debug_mode=False):
    """Starts the Conductor Agent server."""
    try:
        if host is None or port is None:
            from config_loader import get_config_loader
            config_loader = get_config_loader(strict_mode=False)
            default_host, default_port = config_loader.get_agent_host_port('conductor')
            host = host or default_host
            port = port or default_port

        capabilities = AgentCapabilities(
            push_notifications=False,
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
            version="1.0.0",
            default_input_modes=ConductorAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=ConductorAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            supported_interfaces=[
                AgentInterface(
                    protocol_binding="JSONRPC",
                    protocol_version="1.0",
                    url=f"http://{host}:{port}/",
                )
            ],
            skills=[skill],
        )

        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(
            httpx_client=httpx_client, config_store=push_config_store
        )
        request_handler = DefaultRequestHandler(
            agent_executor=ConductorAgentExecutor(),
            task_store=InMemoryTaskStore(),
            agent_card=agent_card,
            push_config_store=push_config_store,
            push_sender=push_sender,
        )
        routes = []
        routes.extend(create_agent_card_routes(agent_card))
        routes.extend(create_jsonrpc_routes(request_handler, "/"))
        app = Starlette(routes=routes)

        if debug_mode or sys.gettrace() is not None:
            import asyncio
            config = uvicorn.Config(app, host=host, port=port, log_level="info")
            server_instance = uvicorn.Server(config)
            asyncio.run(server_instance.serve())
        else:
            uvicorn.run(app, host=host, port=port)

    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
