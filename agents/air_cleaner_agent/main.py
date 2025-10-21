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
from executor import AirPurifierAgentExecutor

memory = MemorySaver()
from agent import AirPurifierAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResponseFormat(BaseModel):
    message: str


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=12002)
def main(host, port):
    """Starts the Air Purifier Agent server."""
    try:
        capabilities = AgentCapabilities(
            type="air_purifier",
            supported_commands=["开启", "关闭", "查询状态", "设置风扇", "设置模式", "调节LED"],
            properties={
                "pm25": 0,
                "humidity": 0,
                "fan_level": 1,
                "mode": 0,
                "power_state": "off",
                "filter_life": 100,
            },
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
