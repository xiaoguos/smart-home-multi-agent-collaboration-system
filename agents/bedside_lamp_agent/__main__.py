"""
主入口点 - 用于 `uv run .` 或 `python -m bedside_lamp_agent` 启动服务
床头灯 Agent
"""

import sys
import os
from pathlib import Path
import dotenv

_CURRENT_DIR = Path(__file__).resolve().parent
_PARENT_DIR = _CURRENT_DIR.parent

# 必须在其他模块导入之前加载 .env，保证模块级环境变量读取正确
dotenv.load_dotenv(dotenv_path=_CURRENT_DIR / ".env", override=True)

if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

import logging
import uvicorn
import httpx
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
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)

from executor import BedsideLampAgentExecutor
from agent import BedsideLampAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Starts the Bedside Lamp Agent server."""
    try:
        host = os.getenv("AGENT_BEDSIDE_LAMP_HOST", "localhost")
        port = int(os.getenv("AGENT_BEDSIDE_LAMP_PORT", "12004"))

        logger.info(f"📍 Bedside Lamp Agent 启动配置: {host}:{port}")

        capabilities = AgentCapabilities(
            push_notifications=False,
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
            version="1.0.0",
            default_input_modes=BedsideLampAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=BedsideLampAgent.SUPPORTED_CONTENT_TYPES,
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
            agent_executor=BedsideLampAgentExecutor(),
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
