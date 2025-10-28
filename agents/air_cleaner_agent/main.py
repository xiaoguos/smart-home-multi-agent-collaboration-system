# 空气净化器 Agent
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
import sys
import click
import logging
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
import httpx
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from executor import AirPurifierAgentExecutor
from agent import AirPurifierAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", "host", default=None, help="服务主机地址（默认从config.yaml读取）")
@click.option("--port", "port", default=None, type=int, help="服务端口（默认从config.yaml读取）")
def main(host, port):
    """Starts the Air Purifier Agent server."""
    try:
        # 从配置文件读取 host 和 port（如果命令行未指定）
        if host is None or port is None:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from config_loader import get_config_loader
            config_loader = get_config_loader(strict_mode=False)
            default_host, default_port = config_loader.get_agent_host_port('air_cleaner')
            host = host or default_host
            port = port or default_port
        
        logger.info(f"📍 Air Cleaner Agent 启动配置: {host}:{port}")
        
        capabilities = AgentCapabilities(
            push_notifications=False,
            state_transition_history=False,
            streaming=False,
        )
        skill = AgentSkill(
            id="control_air_purifier",
            name="Air Purifier Control",
            description="控制桌面空气净化器（zhimi-oa1），包括电源、风扇等级、工作模式、LED亮度，查询PM2.5、湿度、滤芯寿命等",
            tags=["air purifier", "air quality", "PM2.5", "home automation", "smart home"],
            examples=[
                "打开空气净化器",
                "查询当前PM2.5",
                "设置为睡眠模式",
                "把风扇调到高速",
                "关闭LED灯",
            ],
        )
        agent_card = AgentCard(
            name="Air Purifier Agent",
            description="桌面空气净化器（zhimi-oa1）控制的专业助手",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=AirPurifierAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=AirPurifierAgent.SUPPORTED_CONTENT_TYPES,
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
            agent_executor=AirPurifierAgentExecutor(),
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
