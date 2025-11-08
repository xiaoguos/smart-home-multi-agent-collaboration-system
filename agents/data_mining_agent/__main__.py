




"""
主入口点 - 用于 `uv run .` 或 `python -m data_mining_agent` 启动服务
数据挖掘 Agent - 用户行为分析与场景推荐
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

from executor import DataMiningAgentExecutor
from agent import DataMiningAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", "host", default=None, help="服务主机地址（默认从config.yaml读取）")
@click.option("--port", "port", default=None, type=int, help="服务端口（默认从config.yaml读取）")
def main(host, port):
    """Starts the Data Mining Agent server."""
    try:
        # 从配置文件读取 host 和 port（如果命令行未指定）
        if host is None or port is None:
            from config_loader import get_config_loader
            config_loader = get_config_loader(strict_mode=False)
            default_host, default_port = config_loader.get_agent_host_port('data_mining')
            host = host or default_host
            port = port or default_port
        
        capabilities = AgentCapabilities(
            push_notifications=False,
            state_transition_history=False,
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
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=DataMiningAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=DataMiningAgent.SUPPORTED_CONTENT_TYPES,
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
            agent_executor=DataMiningAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=push_config_store,
            push_sender=push_sender,
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        logger.info(f"🚀 数据挖掘 Agent 启动成功")
        logger.info(f"📊 提供用户行为分析与场景挖掘服务")
        logger.info(f"🔗 服务地址: http://{host}:{port}/")
        
        uvicorn.run(server.build(), host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

