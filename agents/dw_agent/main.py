from collections.abc import AsyncIterable
from typing import Any, Literal
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
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

memory = MemorySaver()
from agent import DataMiningAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResponseFormat(BaseModel):
    message: str


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=12003)
def main(host, port):
    """Starts the Data Mining Agent server."""
    try:
        capabilities = AgentCapabilities(
            type="data_mining",
            supported_commands=["分析习惯", "预测偏好", "查看历史", "系统统计"],
            properties={
                "analysis_types": ["user_habits", "preferences", "usage_patterns"],
                "data_sources": ["device_operations", "user_behavior"],
                "supported_devices": ["air_conditioner", "air_cleaner"],
            },
        )
        skill = AgentSkill(
            id="data_mining_analysis",
            name="Data Mining Analysis",
            description="智能家居用户行为数据挖掘和分析系统",
            tags=["data mining", "user behavior", "analytics", "machine learning"],
            examples=[
                "分析用户使用习惯",
                "预测用户温度偏好",
                "查看操作历史记录",
                "生成系统使用报告",
            ],
        )
        agent_card = AgentCard(
            name="Data Mining Agent",
            description="智能家居用户行为数据挖掘和分析专家",
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

        uvicorn.run(server.build(), host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
