"""
主入口点 - 用于 `uv run .` 或 `python -m air_cleaner_agent` 启动服务
空气净化器 Agent
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

from executor import AirPurifierAgentExecutor
from agent import AirPurifierAgent
from skills_catalog import build_air_purifier_skills

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv.load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)


def main():
    """Starts the Air Purifier Agent server."""
    try:
        host = os.getenv("AGENT_AIR_CLEANER_HOST", "localhost")
        port = int(os.getenv("AGENT_AIR_CLEANER_PORT", "12002"))
        
        capabilities = AgentCapabilities(
            push_notifications=False,
            streaming=False,
        )
        skills = build_air_purifier_skills()
        agent_card = AgentCard(
            name="Air Purifier Agent",
            description="桌面空气净化器（zhimi-oa1）控制的专业助手",
            version="1.0.0",
            default_input_modes=AirPurifierAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=AirPurifierAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            supported_interfaces=[
                AgentInterface(
                    protocol_binding="JSONRPC",
                    protocol_version="1.0",
                    url=f"http://{host}:{port}/",
                )
            ],
            skills=skills,
        )

        httpx_client = httpx.AsyncClient()
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(
            httpx_client=httpx_client, config_store=push_config_store
        )
        request_handler = DefaultRequestHandler(
            agent_executor=AirPurifierAgentExecutor(),
            task_store=InMemoryTaskStore(),
            agent_card=agent_card,
            push_config_store=push_config_store,
            push_sender=push_sender,
        )
        routes = []
        routes.extend(create_agent_card_routes(agent_card))
        routes.extend(create_jsonrpc_routes(request_handler, "/"))
        app = Starlette(routes=routes)
        uvicorn.run(app, host=host, port=port)

    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
