"""
主入口点 - 用于 `uv run .` 或 `python -m bedside_lamp_agent` 启动服务
床头灯 Agent
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

from executor import BedsideLampAgentExecutor
from agent import BedsideLampAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", "host", default=None, help="服务主机地址（默认从 .env/config.yaml 读取）")
@click.option("--port", "port", default=None, type=int, help="服务端口（默认从 .env/config.yaml 读取）")
def main(host, port):
    """Starts the Bedside Lamp Agent server."""
    try:
        # 从配置文件读取 host 和 port（如果命令行未指定）
        if host is None or port is None:
            from config_loader import get_config_loader
            config_loader = get_config_loader(strict_mode=False)
            default_host, default_port = config_loader.get_agent_host_port('bedside_lamp')
            host = host or default_host
            port = port or default_port
        
        logger.info(f"📍 Bedside Lamp Agent 启动配置: {host}:{port}")
        
        capabilities = AgentCapabilities(
            push_notifications=False,
            state_transition_history=False,
            streaming=False,
        )
        skill = AgentSkill(
            id="control_bedside_lamp",
            name="Bedside Lamp Control",
            description="控制Yeelink床头灯（yeelink.light.bslamp2），包括电源、亮度、色温、颜色设置，支持阅读、睡眠、浪漫、夜灯等场景模式",
            tags=["bedside lamp", "yeelink", "lighting", "smart home", "home automation"],
            examples=[
                "打开床头灯",
                "调到50%亮度",
                "设置暖光",
                "变成粉色",
                "切换到阅读模式",
                "关闭床头灯",
            ],
        )
        agent_card = AgentCard(
            name="Bedside Lamp Agent",
            description="Yeelink床头灯（yeelink.light.bslamp2）控制的专业助手",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=BedsideLampAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=BedsideLampAgent.SUPPORTED_CONTENT_TYPES,
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
            agent_executor=BedsideLampAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=push_config_store,
            push_sender=push_sender,
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        uvicorn.run(server.build(), host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
