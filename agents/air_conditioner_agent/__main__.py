"""
主入口点 - 用于 `uv run .` 或 `python -m air_conditioner_agent` 启动服务
空调 Agent
"""

import sys
import os
from pathlib import Path
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

_CURRENT_DIR = Path(__file__).resolve().parent
_PARENT_DIR = _CURRENT_DIR.parent

# 必须在导入 agent/tools 之前加载 .env，确保模块级环境变量正确读取
dotenv.load_dotenv(dotenv_path=_CURRENT_DIR / ".env", override=True)

if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from executor import AirConditionerAgentExecutor
from agent import AirConditionerAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Starts the Air Conditioner Agent server."""
    try:
        host = os.getenv("AGENT_AIR_CONDITIONER_HOST", "localhost")
        port = int(os.getenv("AGENT_AIR_CONDITIONER_PORT", "12001"))

        capabilities = AgentCapabilities(
            push_notifications=False,
            streaming=False,
        )
        skill = AgentSkill(
            id="control_air_conditioner",
            name="Air Conditioner Control",
            description="控制家庭空调系统，包括温度，模式和电源设置",
            tags=["air conditioning", "climate control", "home automation"],
            examples=[
                "Set AC to 22 degrees",
                "Turn on the air conditioner",
                "Change AC mode to cooling",
            ],
        )
        agent_card = AgentCard(
            name="Air Conditioner Agent",
            description="家用空调系统控制的专业助手",
            version="1.0.0",
            default_input_modes=AirConditionerAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=AirConditionerAgent.SUPPORTED_CONTENT_TYPES,
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
            agent_executor=AirConditionerAgentExecutor(),
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
