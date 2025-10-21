from collections.abc import AsyncIterable
from typing import Any
from pydantic import BaseModel
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
from executor import DataMiningAgentExecutor
from agent import DataMiningAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResponseFormat(BaseModel):
    message: str


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=12003)
def main(host, port):
    """启动数据挖掘Agent服务器"""
    try:
        capabilities = AgentCapabilities(
            type="data_mining",
            supported_commands=["场景识别", "习惯分析", "偏好挖掘", "行为预测"],
            properties={
                "database_type": "starrocks",
                "analysis_methods": ["scene_recognition", "pattern_analysis", "preference_mining", "action_prediction"],
                "supported_scenes": ["睡觉", "起床", "离家", "回家", "工作", "休息"],
            },
        )
        skill = AgentSkill(
            id="mine_user_behavior",
            name="User Behavior Data Mining",
            description=(
                "用户行为数据挖掘服务，基于StarRocks数据库分析用户的智能家居设备使用习惯。"
                "主要功能："
                "1. 场景识别：理解用户自然语言，识别当前场景（如'我睡觉了' → '睡觉'场景）"
                "2. 习惯挖掘：分析历史数据，发现用户在特定场景下的设备使用模式"
                "3. 智能建议：为中央agent提供个性化的设备控制建议（如睡觉时空调温度、床头灯亮度）"
                "4. 偏好分析：识别用户对各设备的偏好设置"
            ),
            tags=["data mining", "user behavior", "pattern analysis", "habit recognition", "smart recommendations", "RAG", "StarRocks"],
            examples=[
                "我要睡觉了，帮我分析一下我平时睡觉时的设备使用习惯",
                "分析我对空调的使用偏好",
                "现在这个时间我通常会做什么操作",
                "起床场景下给我一些设备控制建议",
                "分析我最近30天的设备使用模式",
            ],
        )
        agent_card = AgentCard(
            name="Data Mining Agent",
            description="用户行为数据挖掘助手，基于StarRocks数据库和RAG技术分析智能家居使用习惯",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=DataMiningAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=DataMiningAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
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
            push_config_store=push_config_store,
            push_sender=push_sender,
        )
        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        logger.info(f"数据挖掘Agent服务器启动在 {host}:{port}")
        logger.info("支持的场景: 睡觉、起床、离家、回家、工作、休息")
        uvicorn.run(server.build(), host=host, port=port)

    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

