# 空调 Agent
from langgraph.checkpoint.memory import MemorySaver
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
from executor import AirConditionerAgentExecutor

memory = MemorySaver()
from agent import AirConditionerAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResponseFormat(BaseModel):
    message: str


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=12001)
def main(host, port):
    """Starts the Currency Agent server."""
    try:
        capabilities = AgentCapabilities(
            push_notifications=False,
            state_transition_history=False,
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
            url=f"http://{host}:{port}/",
            version="1.0.0",
            default_input_modes=AirConditionerAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=AirConditionerAgent.SUPPORTED_CONTENT_TYPES,
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
            agent_executor=AirConditionerAgentExecutor(),
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

