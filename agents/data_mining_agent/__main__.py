"""
主入口点 - 用于 `uv run .` 或 `python -m data_mining_agent` 启动服务
数据挖掘 Agent - 用户行为分析与场景推荐
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

_CURRENT_DIR = Path(__file__).resolve().parent
_PARENT_DIR = _CURRENT_DIR.parent
if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from executor import DataMiningAgentExecutor
from agent import DataMiningAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv.load_dotenv(dotenv_path=_CURRENT_DIR / ".env", override=True)


@click.command()
@click.option("--host", default=None, help="服务主机地址（默认从 .env 读取 AGENT_DATA_MINING_HOST）")
@click.option("--port", default=None, type=int, help="服务端口（默认从 .env 读取 AGENT_DATA_MINING_PORT）")
def main(host=None, port=None):
    """Starts the Data Mining Agent server."""
    try:
        if host is None or port is None:
            from config_loader import get_config_loader
            config_loader = get_config_loader(strict_mode=False)
            default_host, default_port = config_loader.get_agent_host_port('data_mining')
            host = host or default_host
            port = port or default_port

        capabilities = AgentCapabilities(
            push_notifications=False,
            streaming=False,
        )
        skill = AgentSkill(
            id="analyze_user_behavior",
            name="User Behavior Analysis & Scene Mining",
            description="使用GMM算法分析用户智能家居使用习惯，提供个性化场景推荐。从StarRocks数据库挖掘设备操作历史，识别用户行为模式。",
            tags=["data mining", "user behavior", "GMM clustering", "scene analysis", "personalization", "smart home"],
            examples=[
                "分析用户睡觉时的习惯",
                "查询用户起床后通常做什么",
                "我要出门了，推荐设备操作",
                "分析用户晚上回家的习惯",
                "查看数据挖掘Agent状态",
            ],
        )
        agent_card = AgentCard(
            name="Data Mining Agent",
            description="智能家居用户行为数据挖掘与场景分析专家。使用高斯混合模型(GMM)对用户历史操作进行场景聚类，为Conductor Agent提供个性化推荐。",
            version="1.0.0",
            default_input_modes=DataMiningAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=DataMiningAgent.SUPPORTED_CONTENT_TYPES,
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
            agent_executor=DataMiningAgentExecutor(),
            task_store=InMemoryTaskStore(),
            agent_card=agent_card,
            push_config_store=push_config_store,
            push_sender=push_sender,
        )
        routes = []
        routes.extend(create_agent_card_routes(agent_card))
        routes.extend(create_jsonrpc_routes(request_handler, "/"))
        app = Starlette(routes=routes)

        logger.info("🚀 数据挖掘 Agent 启动成功")
        logger.info("📊 提供用户行为分析与场景挖掘服务")
        logger.info(f"🔗 服务地址: http://{host}:{port}/")

        uvicorn.run(app, host=host, port=port)

    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
