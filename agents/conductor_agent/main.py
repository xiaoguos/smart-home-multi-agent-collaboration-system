# 家庭管家Agent
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
from executor import ConductorAgentExecutor
from agent import ConductorAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=12000)
@click.option("--debug", "debug_mode", is_flag=True, default=False, help="启用 debug 模式（兼容 PyCharm debugger）")
def main(host, port, debug_mode):
    """Starts the Conductor Agent server."""
    try:
        capabilities = AgentCapabilities(
            push_notifications=False,
            state_transition_history=False,
            streaming=False,
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

        # 检测是否在 PyCharm debugger 中运行
        is_debugging = sys.gettrace() is not None or debug_mode
        
        if is_debugging:
            # PyCharm Debug 模式：使用兼容的方式启动
            logger.info(f"🐛 Starting in DEBUG mode on {host}:{port}")
            logger.info("使用 uvicorn.Config + uvicorn.Server 方式（兼容 PyCharm debugger）")
            
            import asyncio
            config = uvicorn.Config(
                server.build(), 
                host=host, 
                port=port,
                log_level="info"
            )
            server_instance = uvicorn.Server(config)
            asyncio.run(server_instance.serve())
        else:
            # 正常模式：使用标准方式
            logger.info(f"🚀 Starting in NORMAL mode on {host}:{port}")
            uvicorn.run(server.build(), host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]

    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
