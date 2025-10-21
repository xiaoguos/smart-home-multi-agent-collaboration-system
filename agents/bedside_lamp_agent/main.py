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
from executor import BedsideLampAgentExecutor

memory = MemorySaver()
from agent import BedsideLampAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResponseFormat(BaseModel):
    message: str


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=12004)
def main(host, port):
    """Starts the Bedside Lamp Agent server."""
    try:
        capabilities = AgentCapabilities(
            type="bedside_lamp",
            supported_commands=["开启", "关闭", "查询状态", "设置亮度", "设置色温", "设置颜色", "场景模式"],
            properties={
                "power_state": "off",
                "brightness": 0,
                "color_temp": 4000,
                "color_mode": 1,
                "color": 0,
            },
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

