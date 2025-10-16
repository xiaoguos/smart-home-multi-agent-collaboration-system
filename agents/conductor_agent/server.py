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
from agent_executor import ConductorAgentExecutor

memory = MemorySaver()
from main import ConductorAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResponseFormat(BaseModel):
    message: str


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=12002)
def main(host, port):
    """Starts the Conductor Agent server."""
    try:
        capabilities = AgentCapabilities(
            type="conductor",
            supported_commands=["管理代理", "控制设备", "系统监控", "状态查询", "行为分析", "用户洞察"],
            properties={
                "managed_agents": ["air_conditioner", "air_cleaner", "data_mining"],
                "system_status": "running",
                "total_devices": 3,
                "logging_enabled": True,
            },
        )
        skill = AgentSkill(
            id="smart_home_management",
            name="Smart Home Management",
            description="智能家居总管理系统，协调和管理所有智能设备代理",
            tags=["smart home", "home automation", "agent management", "device control"],
            examples=[
                "查看所有可用代理",
                "控制空调温度",
                "检查系统状态",
                "管理空气净化器",
                "分析我的使用习惯",
                "获取个性化建议",
            ],
        )
        agent_card = AgentCard(
            name="Conductor Agent",
            description="智能家居总管理助手，负责协调和管理所有智能设备代理",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=ConductorAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=ConductorAgent.SUPPORTED_CONTENT_TYPES,
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
            agent_executor=ConductorAgentExecutor(),
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
